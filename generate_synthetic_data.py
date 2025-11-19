import json
import random

def generate_synthetic_data():
    print("Generating synthetic dataset...")
    
    topics = [
        "Cyber Security Policy", "Acceptable Use Policy", "Password Policy", 
        "Data Classification", "Remote Access", "Email Usage", 
        "Incident Response", "Software Installation", "Network Security", "Cloud Storage"
    ]
    
    questions = [
        "What is the objective of the {topic}?",
        "Who is responsible for enforcing the {topic}?",
        "What are the penalties for violating the {topic}?",
        "How do I report a breach of the {topic}?",
        "Does the {topic} apply to students?"
    ]
    
    data = []
    for i in range(50):
        topic = random.choice(topics)
        q_template = random.choice(questions)
        question = q_template.format(topic=topic)
        
        data.append({
            "question": question,
            "ground_truth": f"The {topic} ensures the confidentiality, integrity, and availability of University assets. Violations may result in disciplinary action.",
            "context_source": f"{topic} Document",
            "evolution_type": "simple"
        })
        
    output_file = "synthetic_dataset.json"
    with open(output_file, "w") as f:
        json.dump(data, f, indent=4)
        
    print(f"Successfully generated {len(data)} items to {output_file}")

if __name__ == "__main__":
    generate_synthetic_data()
