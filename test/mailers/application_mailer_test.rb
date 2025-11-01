require "test_helper"

class ApplicationMailerTest < ActionMailer::TestCase
  test "default from address is set" do
    assert_equal "from@example.com", ApplicationMailer.default[:from]
  end

  test "mailer layout is configured" do
    assert_equal "mailer", ApplicationMailer._layout
  end

  test "ApplicationMailer can be instantiated" do
    assert_nothing_raised do
      ApplicationMailer.new
    end
  end
end

