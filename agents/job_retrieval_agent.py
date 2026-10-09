import os
import numpy as np
import pandas as pd
import faiss

from google import genai
from google.genai import types
from dotenv import load_dotenv


load_dotenv()


class JobRetrievalAgent:

    def __init__(self, client=None):

        # ---------------------------------------------
        # Paths
        # ---------------------------------------------

        base_dir = os.path.dirname(
            os.path.dirname(
                os.path.abspath(__file__)
            )
        )

        self.index_file = os.path.join(
            base_dir,
            "data",
            "job_faiss.index"
        )

        self.chunks_file = os.path.join(
            base_dir,
            "data",
            "job_chunks.csv"
        )

        self.jobs_file = os.path.join(
            base_dir,
            "data",
            "job_postings_clean.csv"
        )

        # ---------------------------------------------
        # Gemini Service / Client
        # ---------------------------------------------

        if client:

            # Normal CareerAI path:
            # GeminiService is passed from app.py
            self.client = client

        else:

            # Standalone fallback.
            # This keeps the agent usable even if it is
            # created without GeminiService.

            api_key = os.getenv(
                "GEMINI_API_KEY"
            )

            if not api_key:

                raise ValueError(
                    "GEMINI_API_KEY is not set."
                )

            self.client = genai.Client(
                api_key=api_key
            )

        # ---------------------------------------------
        # Load FAISS index
        # ---------------------------------------------

        if not os.path.exists(
            self.index_file
        ):

            raise FileNotFoundError(
                f"FAISS index not found: {self.index_file}"
            )

        self.index = faiss.read_index(
            self.index_file
        )

        # ---------------------------------------------
        # Load chunk metadata
        # ---------------------------------------------

        if not os.path.exists(
            self.chunks_file
        ):

            raise FileNotFoundError(
                f"Job chunks file not found: {self.chunks_file}"
            )

        self.chunks_df = pd.read_csv(
            self.chunks_file
        )

        # ---------------------------------------------
        # Load complete job records
        # ---------------------------------------------

        if not os.path.exists(
            self.jobs_file
        ):

            raise FileNotFoundError(
                f"Job postings file not found: {self.jobs_file}"
            )

        self.jobs_df = pd.read_csv(
            self.jobs_file
        )

        print(
            "M2: Job Retrieval Agent initialized successfully."
        )

        print(
            f"M2: FAISS index contains "
            f"{self.index.ntotal} vectors."
        )

        print(
            f"M2: Loaded "
            f"{len(self.jobs_df)} job records."
        )

    # =================================================
    # Create search query from candidate profile
    # =================================================

    def build_query(
        self,
        candidate_profile
    ):

        skills = candidate_profile.get(
            "skills",
            []
        )

        education = candidate_profile.get(
            "education",
            []
        )

        experience = candidate_profile.get(
            "experience",
            []
        )

        projects = candidate_profile.get(
            "projects",
            []
        )

        certifications = candidate_profile.get(
            "certifications",
            []
        )

        query_parts = []

        if skills:

            query_parts.append(
                "Skills: " + ", ".join(
                    map(str, skills)
                )
            )

        if education:

            query_parts.append(
                "Education: " + ", ".join(
                    map(str, education)
                )
            )

        if experience:

            query_parts.append(
                "Experience: " + ", ".join(
                    map(str, experience)
                )
            )

        if projects:

            query_parts.append(
                "Projects: " + ", ".join(
                    map(str, projects)
                )
            )

        if certifications:

            query_parts.append(
                "Certifications: " + ", ".join(
                    map(str, certifications)
                )
            )

        return "\n".join(
            query_parts
        )

    # =================================================
    # Generate query embedding
    # =================================================

    def create_embedding(
        self,
        query
    ):

        if not query or not query.strip():

            raise ValueError(
                "Embedding query cannot be empty."
            )

        print(
            "M2: Creating query embedding..."
        )

        # ---------------------------------------------
        # Normal CareerAI path
        # ---------------------------------------------
        # GeminiService provides the centralized
        # embedding method.

        if hasattr(
            self.client,
            "embed"
        ):

            response = self.client.embed(
                query
            )

        # ---------------------------------------------
        # Standalone fallback path
        # ---------------------------------------------
        # Used only when a direct Google Gemini client
        # was supplied instead of GeminiService.

        else:

            response = self.client.models.embed_content(

                model="gemini-embedding-001",

                contents=query,

                config=types.EmbedContentConfig(

                    task_type="RETRIEVAL_QUERY",

                    output_dimensionality=768
                )
            )

        # ---------------------------------------------
        # Convert Gemini embedding to NumPy vector
        # ---------------------------------------------

        vector = np.array(
            response.embeddings[0].values,
            dtype="float32"
        )

        # ---------------------------------------------
        # Verify embedding dimension
        # ---------------------------------------------

        if vector.shape[0] != 768:

            raise ValueError(
                "Embedding dimension mismatch. "
                f"Expected 768, got {vector.shape[0]}."
            )

        # ---------------------------------------------
        # Reshape for FAISS
        # ---------------------------------------------

        vector = vector.reshape(
            1,
            -1
        )

        # ---------------------------------------------
        # Normalize for cosine similarity
        # ---------------------------------------------

        faiss.normalize_L2(
            vector
        )

        print(
            "M2: Query embedding created successfully."
        )

        return vector

    # =================================================
    # Retrieve relevant jobs
    # =================================================

    def retrieve_jobs(
        self,
        candidate_profile,
        top_k_chunks=15,
        top_k_jobs=5
    ):

        # ---------------------------------------------
        # Build query
        # ---------------------------------------------

        query = self.build_query(
            candidate_profile
        )

        if not query:

            print(
                "M2: Candidate profile contains "
                "no information for job retrieval."
            )

            return []

        print(
            "M2: Searching jobs using candidate profile..."
        )

        # ---------------------------------------------
        # Create embedding
        # ---------------------------------------------

        query_vector = self.create_embedding(
            query
        )

        # ---------------------------------------------
        # Search FAISS
        # ---------------------------------------------

        scores, indices = self.index.search(
            query_vector,
            top_k_chunks
        )

        # ---------------------------------------------
        # Collect jobs
        # ---------------------------------------------

        job_scores = {}

        for score, index_position in zip(
            scores[0],
            indices[0]
        ):

            if index_position < 0:

                continue

            chunk = self.chunks_df.iloc[
                index_position
            ]

            jobid = str(
                chunk["jobid"]
            )

            # Keep highest score for each job

            if (
                jobid not in job_scores
                or score > job_scores[jobid]
            ):

                job_scores[jobid] = float(
                    score
                )

        # ---------------------------------------------
        # M4.3 — FILTER AND SORT RETRIEVED JOBS
        # ---------------------------------------------

        MIN_RETRIEVAL_SCORE = 0.20

        filtered_job_scores = {
             jobid: score
            for jobid, score in job_scores.items()
             if score >= MIN_RETRIEVAL_SCORE
        }

        print(
        f"M4.3 RAG: {len(job_scores)} jobs before "
        f"similarity filtering." 
        )

        print(
        f"M4.3 RAG: {len(filtered_job_scores)} jobs after "
        f"similarity filtering."
        )

        ranked_jobs = sorted(
        filtered_job_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

        # ---------------------------------------------
        # Get complete job information
        # ---------------------------------------------

        results = []

        for rank, (jobid, score) in enumerate(
                        ranked_jobs,
                        start=1
                            ):

            matching_rows = self.jobs_df[
                self.jobs_df["jobid"].astype(str)
                == jobid
            ]

            if matching_rows.empty:

                continue

            job = matching_rows.iloc[0]

            results.append({

                "jobid": jobid,

                "job_title": str(
                    job["jobtitle"]
                ),

                "company": str(
                    job["company"]
                ),

                "category": str(
                    job["category"]
                ),

                "skills": str(
                    job["skills"]
                ),

                "experience": str(
                    job["experience"]
                ),

                "education": str(
                    job["education"]
                ),

                "industry": str(
                    job["industry"]
                ),

                "location": str(
                    job["joblocation_address"]
                ),

                "jobdescription": str(
                    job["jobdescription"]
                ),

                "retrieval_score": round(
                    score,
                    4
                ),
                "retrieval_rank": rank


            })

            if len(results) >= top_k_jobs:

                break

               # ---------------------------------------------
        # Retrieval summary
        # ---------------------------------------------

        print(
            f"M2: Retrieved {len(results)} relevant jobs."
        )

        # ---------------------------------------------
        # M4.3 RETRIEVAL QUALITY SUMMARY
        # ---------------------------------------------

        if results:

            retrieval_scores = [
                job["retrieval_score"]
                for job in results
            ]

            print(
                f"M4.3 RAG TOP SCORE: "
                f"{max(retrieval_scores):.4f}"
            )

            print(
                f"M4.3 RAG LOWEST SCORE: "
                f"{min(retrieval_scores):.4f}"
            )

            print(
                f"M4.3 RAG AVERAGE SCORE: "
                f"{sum(retrieval_scores) / len(retrieval_scores):.4f}"
            )

            print(
                "M4.3 RAG RETRIEVED JOBS:"
            )

            for rank, job in enumerate(
                results,
                start=1
            ):

                print(
                    f"  {rank}. "
                    f"{job['job_title']} | "
                    f"{job['company']} | "
                    f"score={job['retrieval_score']:.4f}"
                )

        else:

            print(
                "M4.3 RAG: No jobs retrieved."
            )

        return results