"""Embed the destination guide PDFs into Chroma; retrieve grounded chunks.

Mirrors genai's pdf_embedder. The Chroma store (data/chroma_db/) is gitignored
and auto-built on first retrieval, so a cold deploy rebuilds it from the PDFs.
"""
import pathlib
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()  # idempotent; pulls OPENAI_API_KEY from .env (move to entry point later)

ROOT = pathlib.Path(__file__).resolve().parents[4]
GUIDES_DIR = ROOT / "data" / "destinations"
PERSIST_DIR = ROOT / "data" / "chroma_db"


def get_retriever(k=4):
    """Retriever over the destination guides; builds the store on first use."""
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    if not PERSIST_DIR.exists():                 # cold start -> embed once
        _build_store(embeddings)
    store = Chroma(persist_directory=str(PERSIST_DIR), embedding_function=embeddings)
    return store.as_retriever(search_kwargs={"k": k})


def _build_store(embeddings):
    """Load the guide PDFs, chunk 500/50, embed, and persist to Chroma."""
    docs = PyPDFDirectoryLoader(str(GUIDES_DIR)).load()
    chunks = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50).split_documents(docs)
    Chroma.from_documents(chunks, embeddings, persist_directory=str(PERSIST_DIR))


if __name__ == "__main__":
    _build_store(OpenAIEmbeddings(model="text-embedding-3-small"))
    print("chroma store built")
