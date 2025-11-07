class CreateFailedLoginAttempts < ActiveRecord::Migration[8.1]
  def change
    create_table :failed_login_attempts do |t|
      t.references :user, null: true, foreign_key: true, index: true
      t.datetime :failed_at, null: false
      t.string :ip_address

      t.timestamps
    end

    # Add additional indexes (user_id index is already created by t.references)
    add_index :failed_login_attempts, :ip_address unless index_exists?(:failed_login_attempts, :ip_address)
    add_index :failed_login_attempts, :failed_at unless index_exists?(:failed_login_attempts, :failed_at)
  end
end
