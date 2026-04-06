export type TaskAssigneeOption = { uuid: string; email: string }

export type TaskCardDto = {
  uuid: string
  title: string
  description: string | null
  position: number
  list_uuid: string
  project_uuid: string | null
  created_at: string
  created_by_uuid: string | null
  creator_email: string | null
  assignee_uuid: string | null
  assignee_email: string | null
  archived: boolean
  archived_at: string | null
}

export type TaskListDto = {
  uuid: string
  title: string
  position: number
  cards: TaskCardDto[]
}

export type TaskBoardDto = {
  lists: TaskListDto[]
  archived_cards: TaskCardDto[]
}
