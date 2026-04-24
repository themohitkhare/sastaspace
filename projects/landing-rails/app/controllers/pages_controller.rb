class PagesController < ApplicationController
  allow_unauthenticated_access only: :home

  def home
    # Load projects from public.projects (unmanaged, SQL-migration-owned table).
    # Degrade gracefully if table doesn't exist yet (fresh dev env).
    @projects = Project.order(Arel.sql("live_at DESC NULLS LAST")).all
  rescue ActiveRecord::StatementInvalid
    @projects = []
  end
end
