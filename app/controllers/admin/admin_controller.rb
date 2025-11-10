# Admin dashboard controller
# Provides access to monitoring and administrative features
module Admin
  class AdminController < ApplicationController
    include AdminAuthorizable

    def dashboard
      @job_health = JobMonitoringService.queue_health
      @capacity_metrics = JobMonitoringService.capacity_metrics

      respond_to do |format|
        format.html
      end
    end

    def job_monitoring
      @job_health = JobMonitoringService.queue_health
      @job_metrics = JobMonitoringService.job_metrics(time_window: 1.hour)
      @failure_metrics = JobMonitoringService.failure_metrics(time_window: 1.hour)

      respond_to do |format|
        format.html
      end
    end

    def job_class_metrics
      @job_class = params[:job_class] || "AnalyzeClothingImageJob"
      @metrics = JobMonitoringService.job_class_metrics(@job_class, time_window: 1.hour)

      respond_to do |format|
        format.html
      end
    end
  end
end
