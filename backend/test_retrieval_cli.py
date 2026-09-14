import sys
from backend.retrieval import RetrievalService

TEST_QUESTIONS = [
    "How should top PMs think about user activation in PLG products?",
    "What advice do guests give about pricing and packaging SaaS products?",
    "How do you determine product-market fit according to Lenny's guests?",
    "What are effective strategies for hiring early product managers?",
    "How do growth leaders approach retention versus acquisition?"
]

def main():
    print("Initializing Retrieval Service...")
    service = RetrievalService()
    
    print("\n=================== RETRIEVAL TEST HARNESS ===================\n")
    for idx, q in enumerate(TEST_QUESTIONS, 1):
        print(f"[{idx}] Query: '{q}'")
        res = service.retrieve(q, top_k=3)
        print(f"    Aggregate Retrieval Score: {res['aggregate_score']:.4f}")
        print("    Top Chunks:")
        for rank, chunk in enumerate(res["chunks"], 1):
            print(f"      ({rank}) Score: {chunk['relevance_score']:.4f} | Episode: {chunk['episode_title']} | Guest: {chunk['guest_name']} | Timestamp: {chunk['approx_timestamp']}")
            snippet = chunk['content'][:150].replace('\n', ' ')
            print(f"          Snippet: \"{snippet}...\"")
        print("-" * 65)

if __name__ == "__main__":
    main()
