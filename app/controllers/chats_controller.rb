class ChatsController < ApplicationController
  # This is a basic demo controller for testing RubyLLM integration
  # In production, this would be in app/controllers/api/v1/chats_controller.rb

  before_action :set_chat, only: [ :show, :stream ]

  def index
    @chats = Chat.order(created_at: :desc)
  end

  def show
    @messages = @chat.messages.order(created_at: :asc)
  end

  def new
    @chat = Chat.new
  end

  def create
    @chat = Chat.create!(chat_params)

    # Add the initial user message
    @chat.ask(params[:message], model: params[:model] || "gpt-4o-mini")

    redirect_to @chat
  rescue StandardError => e
    @error = e.message
    render :new, status: :unprocessable_entity
  end

  def stream
    @chat.ask(params[:message], model: params[:model] || "gpt-4o-mini") do |message|
      # Streaming happens via Turbo Streams
      # Log the progress for debugging
      Rails.logger.info "Streaming token: #{message.content}" unless message.content.empty?
    end

    redirect_to @chat
  end

  private

  def set_chat
    @chat = Chat.find(params[:id])
  end

  def chat_params
    params.require(:chat).permit(:model_name)
  end
end

