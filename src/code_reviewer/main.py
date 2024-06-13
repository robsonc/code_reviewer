#!/usr/bin/env python
from code_reviewer.crew import CodeReviewerCrew

project_id = input("Enter the project id: ")

def run():
    # Replace with your inputs, it will automatically interpolate any tasks and agents information
    inputs = {
        'project_id': project_id
    }
    crew = CodeReviewerCrew().crew()
    crew.kickoff(inputs=inputs)
    
    print(crew.usage_metrics)