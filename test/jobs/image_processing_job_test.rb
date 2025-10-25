require 'test_helper'

class ImageProcessingJobTest < ActiveJob::TestCase
  setup do
    @user = users(:one)
    @category = categories(:one)
    @inventory_item = @user.inventory_items.create!(
      name: 'Test Item',
      item_type: 'clothing',
      category: @category
    )
  end

  test 'should process primary image variants' do
    # Attach a test image
    @inventory_item.primary_image.attach(
      io: File.open(Rails.root.join('test', 'fixtures', 'files', 'sample_image.jpg')),
      filename: 'test.jpg',
      content_type: 'image/jpeg'
    )

    assert_enqueued_with(job: ImageProcessingJob) do
      ImageProcessingJob.perform_now(@inventory_item)
    end
  end

  test 'should process additional image variants' do
    # Attach additional images
    @inventory_item.additional_images.attach([
      {
        io: File.open(Rails.root.join('test', 'fixtures', 'files', 'sample_image.jpg')),
        filename: 'test1.jpg',
        content_type: 'image/jpeg'
      },
      {
        io: File.open(Rails.root.join('test', 'fixtures', 'files', 'sample_image.jpg')),
        filename: 'test2.jpg',
        content_type: 'image/jpeg'
      }
    ])

    additional_image = @inventory_item.additional_images.first

    assert_nothing_raised do
      ImageProcessingJob.perform_now(@inventory_item, additional_image.id)
    end
  end

  test 'should handle missing image gracefully' do
    assert_nothing_raised do
      ImageProcessingJob.perform_now(@inventory_item, 99999)
    end
  end

  test 'should handle image processing errors gracefully' do
    # Mock an error during variant generation
    ActiveStorage::Variant.stub(:new, -> { raise StandardError.new('Processing error') }) do
      @inventory_item.primary_image.attach(
        io: File.open(Rails.root.join('test', 'fixtures', 'files', 'sample_image.jpg')),
        filename: 'test.jpg',
        content_type: 'image/jpeg'
      )

      assert_raises(StandardError) do
        ImageProcessingJob.perform_now(@inventory_item)
      end
    end
  end
end
