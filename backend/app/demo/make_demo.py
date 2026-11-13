"""Generates demo_comments.csv - a SYNTHETIC sample dataset used only by the 'Load Demo Dataset' button.
It is labelled 'Demo Dataset' everywhere in the product and is processed by the exact same pipeline as real data."""
import csv
import random
from datetime import date, timedelta

R = random.Random(2026)
OPEN = ["", "", "Honestly, ", "Hey, ", "Quick question: ", "Been stuck for days - ", "Great channel btw. ", "Not gonna lie, ", "Please help: "]
TOPICS = {
 "docker_net": (38, 2.2, [
  "I can't understand how Docker containers talk to each other over bridge networks",
  "Docker networking is so confusing, what is the difference between bridge and host mode?",
  "my container can't reach the database container even though they're on the same compose network",
  "can you explain docker compose networks and service discovery from scratch?",
  "how do I expose a container port to the outside world without breaking everything",
  "tried three tutorials on container networking and I still don't get overlay networks",
  "localhost inside a docker container never points to my host machine, why?",
  "please make a beginner video on docker network drivers and DNS between containers",
  "getting connection refused between two docker services, no idea how to debug networking",
  "what actually happens to ports when I use -p 8080:80 in docker run?"]),
 "ml_deploy": (34, 1.8, [
  "How do I deploy my ML model so other people can actually use it?",
  "I trained a model in a notebook but have no idea how to put it into production",
  "can you do a tutorial on serving a scikit-learn model with FastAPI and docker?",
  "model deployment is the part nobody teaches, I'm lost after training",
  "what's the best way to host a pytorch model cheaply for a portfolio project",
  "how do I monitor a deployed model for drift and retrain it?",
  "my inference API is really slow in production, how do I optimize model serving",
  "please cover MLOps basics: versioning, CI/CD and deploying models to the cloud",
  "deploying a machine learning model to AWS confuses me, which service should I use?",
  "I don't know how to turn my jupyter notebook into a real deployed application"]),
 "genai_portfolio": (30, 1.5, [
  "What GenAI projects should I build to get hired as a fresher?",
  "recruiters keep ignoring my AI portfolio, what do they actually look for?",
  "can you make a roadmap for building a generative AI portfolio from zero?",
  "I'm a student and I don't know which LLM projects look impressive on a resume",
  "how many projects should be on my github for an AI internship?",
  "is a RAG chatbot a good portfolio project or is everyone doing it already?",
  "please show how to present AI projects on a resume and linkedin",
  "struggling to find unique GenAI project ideas that aren't just chatbots",
  "do I need deployment and a demo link for my AI portfolio projects?",
  "how do I prepare for AI engineer interviews after building a few projects"]),
 "python_projects": (30, 1.0, [
  "Can you suggest practical python projects for beginners that aren't todo apps?",
  "I finished a python course but I can't build anything on my own",
  "what python project ideas are good for a resume?",
  "please make a video on structuring a python project properly with tests",
  "how do I learn python decorators and generators in a way that sticks?",
  "I struggle to move from tutorials to building real python programs",
  "which python libraries should I learn first for automation?",
  "python virtual environments and packaging are confusing, can you explain?"]),
 "k8s": (28, 0.55, [
  "kubernetes feels overwhelming, where do I even start as a beginner?",
  "can you explain pods versus deployments versus services in kubernetes?",
  "how do I set up a local kubernetes cluster with minikube?",
  "kubernetes ingress controllers confuse me a lot",
  "please make a helm chart tutorial for beginners",
  "what is the difference between kubernetes and docker swarm, which should I learn?",
  "my pods keep crashing with CrashLoopBackOff, how do I debug this?"]),
 "git": (22, 1.0, [
  "git rebase vs merge - when should I use which?",
  "I messed up my git history, how do I undo a force push?",
  "can you make a video about resolving merge conflicts without panicking?",
  "how do branching strategies work on real teams like gitflow or trunk based?",
  "what is git stash and when is it useful?"]),
}
rows, end = [], date(2026, 9, 30)
for key, (n, growth, bank) in TOPICS.items():
    for i in range(n):
        d = int(120 * (R.random() ** (1 / growth)))        # growth>1 skews mentions toward recent days
        ts = end - timedelta(days=120 - d)
        text = (R.choice(OPEN) + R.choice(bank)).strip()
        if text and text[0].islower(): text = text[0].upper() + text[1:]
        likes = int(R.paretovariate(1.6) * 2) % 120
        if R.random() < .35: text += R.choice([" Thanks!", " Would really appreciate this.", " Subscribed already.", " Any help welcome."])
        rows.append({"comment": text, "timestamp": ts.isoformat(), "likes": likes, "replies": R.randint(0, 6) if likes > 8 else 0,
                     "platform": R.choices(["YouTube", "Reddit"], [0.62, 0.38])[0]})
R.shuffle(rows)
with open(__file__.replace("make_demo.py", "demo_comments.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["comment", "timestamp", "likes", "replies", "platform"]); w.writeheader(); w.writerows(rows)
print(len(rows), "rows")
