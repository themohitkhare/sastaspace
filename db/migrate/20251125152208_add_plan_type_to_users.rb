class AddPlanTypeToUsers < ActiveRecord::Migration[8.1]
  def change
    add_column :users, :plan_type, :string, default: "free", null: false
    add_index :users, :plan_type
    add_column :users, :stripe_customer_id, :string
  end
end
