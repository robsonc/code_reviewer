from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from langchain_community.agent_toolkits.gitlab.toolkit import GitLabToolkit
from langchain_community.utilities.gitlab import GitLabAPIWrapper
import gitlab
from gitlab.base import RESTObject
from gitlab.v4.objects import MergeRequest, ProjectMergeRequestDiff
from dotenv import load_dotenv
import os
from crewai_tools import BaseTool
from typing import List
from dataclasses import dataclass
import logging
import http.client
# import logging
# from http import client

load_dotenv()
# Uncomment the following line to use an example of a custom tool
# from code_reviewer.tools.custom_tool import MyCustomTool

# Check our tools documentations for more information on how to use them
# from crewai_tools import SerperDevTool

# gitlab = GitLabAPIWrapper()
# toolkit = GitLabToolkit.from_gitlab_api_wrapper(gitlab)

@dataclass
class MergeRequestInfo:
    iid: int
    title: str
    
    @classmethod
    def from_mergerequest(cls, mr):
        # print(mr.attributes)
        return cls(iid=mr.iid, title=mr.title)  

gl = gitlab.Gitlab(url=os.environ['GITLAB_URL'], private_token=os.environ['GITLAB_PERSONAL_ACCESS_TOKEN'])
#gl.enable_debug()

class GetMergeRequests(BaseTool):
    name: str = "GetMergeRequests"
    description: str = (
        "Get all merge requests from a specific project."
    )

    def _run(self, project_id: int) -> List[object]:
        mrs = gl.mergerequests.list(project_id=project_id, per_page=2, get_all=False)
        return list(map(MergeRequestInfo.from_mergerequest, mrs))
    
class GetMergeRequestByIId(BaseTool):
    name: str = "GetMergeRequestByIId"
    description: str = (
        "Get a specific project merge request by its IID."
    )

    def _run(self, project_id: int, mr_iid: int) -> MergeRequest:
        project = gl.projects.get(project_id)
        editable_mr = project.mergerequests.get(mr_iid)
        
        return editable_mr

class GetMergeRequestDiffs(BaseTool):
    name: str = "GetMergeRequestDiffs"
    description: str = (
        "Get merge request diffs."
    )

    def _run(self, project_id: int, mr_iid: int) -> List[object]:
        project = gl.projects.get(project_id)
        editable_mr = project.mergerequests.get(mr_iid)
        diffs = editable_mr.diffs.list()
        print(diffs[0].attributes)
        return diffs

class GetMergeRequestDiffChanges(BaseTool):
    name: str = "GetMergeRequestDiffChanges"
    description: str = (
        "Get merge request diff changes."
    )

    def _run(self, project_id: int, mr_iid: int) -> List[object]:
        project = gl.projects.get(project_id)
        editable_mr = project.mergerequests.get(mr_iid)
        diffs = editable_mr.diffs.list()
        
        changesList = []
        for diff in diffs:
            changes = diff.changes()
            print(changes)
            changesList.append(changes)
            
        return changesList

get_merge_requests_tool = GetMergeRequests()
get_merge_request_by_iid_tool = GetMergeRequestByIId()
get_merge_request_diffs_tool = GetMergeRequestDiffs()
get_merge_request_diff_changes_tool = GetMergeRequestDiffChanges()

@CrewBase
class CodeReviewerCrew():
	"""CodeReviewer crew"""
	agents_config = 'config/agents.yaml'
	tasks_config = 'config/tasks.yaml'
  
	# AGENTS
	@agent
	def merge_request_finder(self) -> Agent:
		return Agent(
			config=self.agents_config['merge_request_finder'],
			verbose=True,
			allow_delegation=False,
			tools=[get_merge_requests_tool]
		)
  
	@agent
	def merge_request_reviewer(self) -> Agent:
		return Agent(
			config=self.agents_config['merge_request_reviewer'],
			verbose=True,
			tools=[get_merge_request_diffs_tool],
			allow_delegation=False
		)
  
	@agent
	def report_creator(self) -> Agent:
		return Agent(
			config=self.agents_config['report_creator'],
			verbose=True,
			allow_delegation=False
		)
  
	# TASKS
  
	@task
	def find_merge_requests(self) -> Task:
		return Task(
			config=self.tasks_config['find_merge_requests_task'],
			agent=self.merge_request_finder()
		)
  
	@task
	def review_merge_requests(self) -> Task:
		return Task(
			config=self.tasks_config['review_merge_requests_task'],
			agent=self.merge_request_reviewer()
		)
  
	@task
	def create_report(self) -> Task:
		return Task(
			config=self.tasks_config['create_report_review_task'],
			agent=self.report_creator(),
			output_file='report.md'
		)

	@crew
	def crew(self) -> Crew:
		"""Creates the CodeReviewer crew"""
		return Crew(
			agents=self.agents, # Automatically created by the @agent decorator
			tasks=self.tasks, # Automatically created by the @task decorator
			process=Process.sequential,
			verbose=2,
			# process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
		)
