"""Asana integration client for Reflex Executive Assistant."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from dataclasses import dataclass

import asana

from ..config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class AsanaTask:
    """Asana task structure."""
    task_id: str
    name: str
    description: Optional[str] = None
    status: str = "incomplete"
    assignee: Optional[str] = None
    due_date: Optional[date] = None
    project_id: Optional[str] = None
    section_id: Optional[str] = None
    tags: List[str] = None
    notes: Optional[str] = None
    completed: bool = False
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None


@dataclass
class AsanaProject:
    """Asana project structure."""
    project_id: str
    name: str
    description: Optional[str] = None
    status: str = "active"
    team_id: Optional[str] = None
    workspace_id: str
    due_date: Optional[date] = None
    owner: Optional[str] = None
    is_public: bool = True
    color: Optional[str] = None
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None


@dataclass
class AsanaSection:
    """Asana section structure."""
    section_id: str
    name: str
    project_id: str
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None


@dataclass
class AsanaUser:
    """Asana user structure."""
    user_id: str
    name: str
    email: Optional[str] = None
    photo: Optional[str] = None
    is_workspace_admin: bool = False
    is_admin: bool = False


class AsanaClient:
    """Asana API client for project management operations."""
    
    def __init__(self):
        """Initialize the Asana client."""
        self.settings = get_settings()
        self.client = None
        
        # Initialize the client
        self._init_client()
    
    def _init_client(self):
        """Initialize the Asana API client."""
        try:
            # Initialize Asana client with personal access token
            self.client = asana.Client.access_token(self.settings.asana_personal_access_token)
            
            # Test the connection
            user = self.client.users.me()
            user_name = user['name']
            user_id = user['gid']
            
            logger.info(f"Asana client initialized successfully for user: {user_name} ({user_id})")
            
        except Exception as e:
            logger.error(f"Failed to initialize Asana client: {e}")
            raise
    
    async def get_workspaces(self) -> List[Dict[str, Any]]:
        """Get available workspaces."""
        try:
            workspaces = self.client.workspaces.find_all()
            return list(workspaces)
            
        except Exception as e:
            logger.error(f"Error getting workspaces: {e}")
            return []
    
    async def get_projects(
        self,
        workspace_id: Optional[str] = None,
        team_id: Optional[str] = None,
        archived: bool = False
    ) -> List[AsanaProject]:
        """Get projects from workspace or team."""
        try:
            params = {}
            if workspace_id:
                params['workspace'] = workspace_id
            if team_id:
                params['team'] = team_id
            if archived is not None:
                params['archived'] = archived
            
            projects = self.client.projects.find_all(**params)
            
            asana_projects = []
            for project in projects:
                asana_project = AsanaProject(
                    project_id=project['gid'],
                    name=project['name'],
                    description=project.get('notes'),
                    status=project.get('status', 'active'),
                    team_id=project.get('team', {}).get('gid'),
                    workspace_id=project['workspace']['gid'],
                    due_date=project.get('due_date'),
                    owner=project.get('owner', {}).get('gid'),
                    is_public=project.get('public', True),
                    color=project.get('color'),
                    created_at=project.get('created_at'),
                    modified_at=project.get('modified_at')
                )
                asana_projects.append(asana_project)
            
            logger.info(f"Retrieved {len(asana_projects)} projects")
            return asana_projects
            
        except Exception as e:
            logger.error(f"Error getting projects: {e}")
            return []
    
    async def get_project(self, project_id: str) -> Optional[AsanaProject]:
        """Get a specific project by ID."""
        try:
            project = self.client.projects.find_by_id(project_id)
            
            asana_project = AsanaProject(
                project_id=project['gid'],
                name=project['name'],
                description=project.get('notes'),
                status=project.get('status', 'active'),
                team_id=project.get('team', {}).get('gid'),
                workspace_id=project['workspace']['gid'],
                due_date=project.get('due_date'),
                owner=project.get('owner', {}).get('gid'),
                is_public=project.get('public', True),
                color=project.get('color'),
                created_at=project.get('created_at'),
                modified_at=project.get('modified_at')
            )
            
            return asana_project
            
        except Exception as e:
            logger.error(f"Error getting project {project_id}: {e}")
            return None
    
    async def create_project(
        self,
        name: str,
        workspace_id: str,
        team_id: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs
    ) -> Optional[str]:
        """Create a new project."""
        try:
            project_data = {
                'name': name,
                'workspace': workspace_id,
                'notes': description
            }
            
            if team_id:
                project_data['team'] = team_id
            
            # Add additional parameters
            for key, value in kwargs.items():
                if value is not None:
                    project_data[key] = value
            
            project = self.client.projects.create(**project_data)
            project_id = project['gid']
            
            logger.info(f"Created project: {name} with ID {project_id}")
            return project_id
            
        except Exception as e:
            logger.error(f"Error creating project: {e}")
            return None
    
    async def update_project(
        self,
        project_id: str,
        **kwargs
    ) -> bool:
        """Update an existing project."""
        try:
            # Filter out None values
            update_data = {k: v for k, v in kwargs.items() if v is not None}
            
            if not update_data:
                logger.warning("No valid data provided for project update")
                return False
            
            self.client.projects.update(project_id, **update_data)
            
            logger.info(f"Updated project: {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating project {project_id}: {e}")
            return False
    
    async def archive_project(self, project_id: str) -> bool:
        """Archive a project."""
        try:
            self.client.projects.update(project_id, archived=True)
            
            logger.info(f"Archived project: {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error archiving project {project_id}: {e}")
            return False
    
    async def get_project_sections(self, project_id: str) -> List[AsanaSection]:
        """Get sections within a project."""
        try:
            sections = self.client.sections.find_by_project(project_id)
            
            asana_sections = []
            for section in sections:
                asana_section = AsanaSection(
                    section_id=section['gid'],
                    name=section['name'],
                    project_id=project_id,
                    created_at=section.get('created_at'),
                    modified_at=section.get('modified_at')
                )
                asana_sections.append(asana_section)
            
            return asana_sections
            
        except Exception as e:
            logger.error(f"Error getting sections for project {project_id}: {e}")
            return []
    
    async def create_section(
        self,
        name: str,
        project_id: str
    ) -> Optional[str]:
        """Create a new section in a project."""
        try:
            section = self.client.sections.create_in_project(
                project=project_id,
                name=name
            )
            
            section_id = section['gid']
            logger.info(f"Created section: {name} with ID {section_id}")
            return section_id
            
        except Exception as e:
            logger.error(f"Error creating section: {e}")
            return None
    
    async def get_tasks(
        self,
        project_id: Optional[str] = None,
        assignee: Optional[str] = None,
        workspace_id: Optional[str] = None,
        completed: Optional[bool] = None,
        limit: int = 100
    ) -> List[AsanaTask]:
        """Get tasks based on filters."""
        try:
            params = {'limit': limit}
            
            if project_id:
                params['project'] = project_id
            if assignee:
                params['assignee'] = assignee
            if workspace_id:
                params['workspace'] = workspace_id
            if completed is not None:
                params['completed'] = completed
            
            tasks = self.client.tasks.find_all(**params)
            
            asana_tasks = []
            for task in tasks:
                asana_task = AsanaTask(
                    task_id=task['gid'],
                    name=task['name'],
                    description=task.get('notes'),
                    status=task.get('status', 'incomplete'),
                    assignee=task.get('assignee', {}).get('gid'),
                    due_date=task.get('due_on'),
                    project_id=task.get('projects', [{}])[0].get('gid') if task.get('projects') else None,
                    section_id=task.get('memberships', [{}])[0].get('section', {}).get('gid') if task.get('memberships') else None,
                    tags=[tag['name'] for tag in task.get('tags', [])],
                    notes=task.get('notes'),
                    completed=task.get('completed', False),
                    completed_at=task.get('completed_at'),
                    created_at=task.get('created_at'),
                    modified_at=task.get('modified_at')
                )
                asana_tasks.append(asana_task)
            
            logger.info(f"Retrieved {len(asana_tasks)} tasks")
            return asana_tasks
            
        except Exception as e:
            logger.error(f"Error getting tasks: {e}")
            return []
    
    async def get_task(self, task_id: str) -> Optional[AsanaTask]:
        """Get a specific task by ID."""
        try:
            task = self.client.tasks.find_by_id(task_id)
            
            asana_task = AsanaTask(
                task_id=task['gid'],
                name=task['name'],
                description=task.get('notes'),
                status=task.get('status', 'incomplete'),
                assignee=task.get('assignee', {}).get('gid'),
                due_date=task.get('due_on'),
                project_id=task.get('projects', [{}])[0].get('gid') if task.get('projects') else None,
                section_id=task.get('memberships', [{}])[0].get('section', {}).get('gid') if task.get('memberships') else None,
                tags=[tag['name'] for tag in task.get('tags', [])],
                notes=task.get('notes'),
                completed=task.get('completed', False),
                completed_at=task.get('completed_at'),
                created_at=task.get('created_at'),
                modified_at=task.get('modified_at')
            )
            
            return asana_task
            
        except Exception as e:
            logger.error(f"Error getting task {task_id}: {e}")
            return None
    
    async def create_task(
        self,
        name: str,
        project_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        description: Optional[str] = None,
        assignee: Optional[str] = None,
        due_date: Optional[date] = None,
        **kwargs
    ) -> Optional[str]:
        """Create a new task."""
        try:
            task_data = {
                'name': name,
                'notes': description
            }
            
            if project_id:
                task_data['projects'] = [project_id]
            if workspace_id:
                task_data['workspace'] = workspace_id
            if assignee:
                task_data['assignee'] = assignee
            if due_date:
                task_data['due_on'] = due_date.isoformat()
            
            # Add additional parameters
            for key, value in kwargs.items():
                if value is not None:
                    task_data[key] = value
            
            task = self.client.tasks.create(**task_data)
            task_id = task['gid']
            
            logger.info(f"Created task: {name} with ID {task_id}")
            return task_id
            
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return None
    
    async def update_task(
        self,
        task_id: str,
        **kwargs
    ) -> bool:
        """Update an existing task."""
        try:
            # Filter out None values
            update_data = {k: v for k, v in kwargs.items() if v is not None}
            
            if not update_data:
                logger.warning("No valid data provided for task update")
                return False
            
            self.client.tasks.update(task_id, **update_data)
            
            logger.info(f"Updated task: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating task {task_id}: {e}")
            return False
    
    async def complete_task(self, task_id: str) -> bool:
        """Mark a task as completed."""
        try:
            self.client.tasks.update(task_id, completed=True)
            
            logger.info(f"Completed task: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error completing task {task_id}: {e}")
            return False
    
    async def reopen_task(self, task_id: str) -> bool:
        """Reopen a completed task."""
        try:
            self.client.tasks.update(task_id, completed=False)
            
            logger.info(f"Reopened task: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error reopening task {task_id}: {e}")
            return False
    
    async def assign_task(self, task_id: str, assignee_id: str) -> bool:
        """Assign a task to a user."""
        try:
            self.client.tasks.update(task_id, assignee=assignee_id)
            
            logger.info(f"Assigned task {task_id} to user {assignee_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error assigning task {task_id}: {e}")
            return False
    
    async def add_task_to_project(self, task_id: str, project_id: str) -> bool:
        """Add a task to a project."""
        try:
            self.client.tasks.add_project(task_id, project=project_id)
            
            logger.info(f"Added task {task_id} to project {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding task {task_id} to project {project_id}: {e}")
            return False
    
    async def remove_task_from_project(self, task_id: str, project_id: str) -> bool:
        """Remove a task from a project."""
        try:
            self.client.tasks.remove_project(task_id, project=project_id)
            
            logger.info(f"Removed task {task_id} from project {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing task {task_id} from project {project_id}: {e}")
            return False
    
    async def add_task_to_section(self, task_id: str, section_id: str) -> bool:
        """Add a task to a section."""
        try:
            self.client.tasks.add_project(
                task_id,
                project=section_id,
                insert_after=None
            )
            
            logger.info(f"Added task {task_id} to section {section_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding task {task_id} to section {section_id}: {e}")
            return False
    
    async def get_users(
        self,
        workspace_id: Optional[str] = None,
        team_id: Optional[str] = None
    ) -> List[AsanaUser]:
        """Get users from workspace or team."""
        try:
            params = {}
            if workspace_id:
                params['workspace'] = workspace_id
            if team_id:
                params['team'] = team_id
            
            users = self.client.users.find_all(**params)
            
            asana_users = []
            for user in users:
                asana_user = AsanaUser(
                    user_id=user['gid'],
                    name=user['name'],
                    email=user.get('email'),
                    photo=user.get('photo', {}).get('image_128'),
                    is_workspace_admin=user.get('is_workspace_admin', False),
                    is_admin=user.get('is_admin', False)
                )
                asana_users.append(asana_user)
            
            return asana_users
            
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return []
    
    async def get_user(self, user_id: str) -> Optional[AsanaUser]:
        """Get a specific user by ID."""
        try:
            user = self.client.users.find_by_id(user_id)
            
            asana_user = AsanaUser(
                user_id=user['gid'],
                name=user['name'],
                email=user.get('email'),
                photo=user.get('photo', {}).get('image_128'),
                is_workspace_admin=user.get('is_workspace_admin', False),
                is_admin=user.get('is_admin', False)
            )
            
            return asana_user
            
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    async def get_teams(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get teams in a workspace."""
        try:
            teams = self.client.teams.find_by_workspace(workspace_id)
            return list(teams)
            
        except Exception as e:
            logger.error(f"Error getting teams for workspace {workspace_id}: {e}")
            return []
    
    async def create_subtask(
        self,
        name: str,
        parent_task_id: str,
        description: Optional[str] = None,
        assignee: Optional[str] = None,
        **kwargs
    ) -> Optional[str]:
        """Create a subtask."""
        try:
            task_data = {
                'name': name,
                'parent': parent_task_id,
                'notes': description
            }
            
            if assignee:
                task_data['assignee'] = assignee
            
            # Add additional parameters
            for key, value in kwargs.items():
                if value is not None:
                    task_data[key] = value
            
            task = self.client.tasks.create(**task_data)
            task_id = task['gid']
            
            logger.info(f"Created subtask: {name} with ID {task_id}")
            return task_id
            
        except Exception as e:
            logger.error(f"Error creating subtask: {e}")
            return None
    
    async def get_subtasks(self, parent_task_id: str) -> List[AsanaTask]:
        """Get subtasks of a parent task."""
        try:
            subtasks = self.client.tasks.subtasks(parent_task_id)
            
            asana_subtasks = []
            for subtask in subtasks:
                asana_subtask = AsanaTask(
                    task_id=subtask['gid'],
                    name=subtask['name'],
                    description=subtask.get('notes'),
                    status=subtask.get('status', 'incomplete'),
                    assignee=subtask.get('assignee', {}).get('gid'),
                    due_date=subtask.get('due_on'),
                    project_id=subtask.get('projects', [{}])[0].get('gid') if subtask.get('projects') else None,
                    section_id=subtask.get('memberships', [{}])[0].get('section', {}).get('gid') if subtask.get('memberships') else None,
                    tags=[tag['name'] for tag in subtask.get('tags', [])],
                    notes=subtask.get('notes'),
                    completed=subtask.get('completed', False),
                    completed_at=subtask.get('completed_at'),
                    created_at=subtask.get('created_at'),
                    modified_at=subtask.get('modified_at')
                )
                asana_subtasks.append(asana_subtask)
            
            return asana_subtasks
            
        except Exception as e:
            logger.error(f"Error getting subtasks for task {parent_task_id}: {e}")
            return []
    
    async def add_comment_to_task(self, task_id: str, comment_text: str) -> Optional[str]:
        """Add a comment to a task."""
        try:
            story = self.client.stories.create_on_task(
                task_id,
                text=comment_text
            )
            
            story_id = story['gid']
            logger.info(f"Added comment to task {task_id}: {story_id}")
            return story_id
            
        except Exception as e:
            logger.error(f"Error adding comment to task {task_id}: {e}")
            return None
    
    async def get_task_comments(self, task_id: str) -> List[Dict[str, Any]]:
        """Get comments for a task."""
        try:
            stories = self.client.stories.find_by_task(task_id)
            return list(stories)
            
        except Exception as e:
            logger.error(f"Error getting comments for task {task_id}: {e}")
            return []


# Global Asana client instance
_asana_client: Optional[AsanaClient] = None


def get_asana_client() -> AsanaClient:
    """Get the global Asana client instance."""
    global _asana_client
    
    if _asana_client is None:
        _asana_client = AsanaClient()
    
    return _asana_client


async def create_asana_task(
    name: str,
    project_id: str,
    description: Optional[str] = None,
    assignee: Optional[str] = None,
    due_date: Optional[date] = None
) -> Optional[str]:
    """Create an Asana task."""
    client = get_asana_client()
    
    return await client.create_task(
        name=name,
        project_id=project_id,
        description=description,
        assignee=assignee,
        due_date=due_date
    )


async def get_project_tasks(project_id: str) -> List[AsanaTask]:
    """Get all tasks in a project."""
    client = get_asana_client()
    return await client.get_tasks(project_id=project_id) 