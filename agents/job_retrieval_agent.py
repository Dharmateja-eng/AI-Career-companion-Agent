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
        # Gemini client
        # ---------------------------------------------

        if client:

            self.client = client

        else:

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

        self.chunks_df = pd.read_csv(
            self.chunks_file
        )

        # ---------------------------------------------
        # Load complete job records
        # ---------------------------------------------

        self.jobs_df = pd.read_csv(
            self.jobs_file
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

        response = self.client.models.embed_content(

            model="gemini-embedding-001",

            contents=query,

            config=types.EmbedContentConfig(

                task_type="RETRIEVAL_QUERY",

                output_dimensionality=768
            )
        )

        vector = np.array(
            response.embeddings[0].values,
            dtype="float32"
        )

        # Normalize for cosine similarity
        vector = vector.reshape(
            1,
            -1
        )

        faiss.normalize_L2(
            vector
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

            return []


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
        # Sort jobs by retrieval score
        # ---------------------------------------------

        ranked_jobs = sorted(
            job_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )


        # ---------------------------------------------
        # Get complete job information
        # ---------------------------------------------

        results = []


        for jobid, score in ranked_jobs:

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
                )
            })


            if len(results) >= top_k_jobs:

                break


        return results