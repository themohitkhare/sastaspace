class CreateSessions < ActiveRecord::Migration[8.1]
  def change
    # if_not_exists so both landing-rails and almirah-rails can carry this
    # migration without colliding — shared public.sessions table.
    create_table :sessions, if_not_exists: true do |t|
      t.references :user, null: false, foreign_key: true
      t.string :ip_address
      t.string :user_agent

      t.timestamps
    end
  end
end
