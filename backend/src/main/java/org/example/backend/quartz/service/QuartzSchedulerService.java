package org.example.backend.quartz.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.extern.slf4j.Slf4j;
import org.example.backend.common.exception.BusinessException;
import org.example.backend.common.exception.Module;
import org.example.backend.quartz.constant.SysJobConstants;
import org.example.backend.quartz.entity.SysJobEntity;
import org.example.backend.quartz.job.QuartzJob;
import org.quartz.*;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.util.List;

@Slf4j
@Service
public class QuartzSchedulerService {

    @Resource
    private Scheduler scheduler;

    @Resource
    private SysJobService sysJobService;

    public void loadAvailableTasks() {
        List<SysJobEntity> jobs = sysJobService.list(
                new LambdaQueryWrapper<SysJobEntity>().eq(SysJobEntity::getEnabled, SysJobConstants.ENABLED_YES)
        );
        log.info("从 sys_job 加载已启用任务，共 {} 条", jobs.size());

        for (SysJobEntity job : jobs) {
            try {
                addOrUpdateJob(job);
                log.info("已加载定时任务: jobId={}, name={}", job.getJobId(), job.getJobName());
            } catch (SchedulerException e) {
                log.error("加载定时任务失败: jobId={}, name={}", job.getJobId(), job.getJobName(), e);
            }
        }
    }

    public void syncJob(SysJobEntity job) {
        try {
            if (SysJobConstants.ENABLED_YES.equals(job.getEnabled())) {
                addOrUpdateJob(job);
            } else {
                removeJob(job.getJobId());
            }
        } catch (SchedulerException e) {
            log.error("同步 Quartz 任务失败: jobId={}", job.getJobId(), e);
            throw new BusinessException(Module.ModuleType.QUARTZ, "调度器同步失败", e);
        }
    }

    public void addOrUpdateJob(SysJobEntity job) throws SchedulerException {
        JobKey jobKey = getJobKey(job.getJobId());
        TriggerKey triggerKey = getTriggerKey(job.getJobId());

        if (scheduler.checkExists(jobKey)) {
            scheduler.deleteJob(jobKey);
        }

        JobDetail jobDetail = JobBuilder.newJob(QuartzJob.class)
                .withIdentity(jobKey)
                .withDescription(job.getDescription())
                .usingJobData("jobId", job.getJobId())
                .usingJobData("beanName", job.getBeanName())
                .build();

        CronTrigger trigger = TriggerBuilder.newTrigger()
                .withIdentity(triggerKey)
                .withSchedule(CronScheduleBuilder.cronSchedule(job.getCronExpression()))
                .forJob(jobDetail)
                .build();

        scheduler.scheduleJob(jobDetail, trigger);
        log.info("已同步 Quartz 任务: jobId={}, cron={}", job.getJobId(), job.getCronExpression());
    }

    public void removeJob(Long jobId) throws SchedulerException {
        JobKey jobKey = getJobKey(jobId);
        if (scheduler.checkExists(jobKey)) {
            scheduler.deleteJob(jobKey);
            log.info("已从 Quartz 移除任务: jobId={}", jobId);
        }
    }

    public void triggerJob(Long jobId) throws SchedulerException {
        JobKey jobKey = getJobKey(jobId);
        if (!scheduler.checkExists(jobKey)) {
            throw new BusinessException(Module.ModuleType.QUARTZ, "任务尚未注册到调度器，请先启用", null);
        }
        scheduler.triggerJob(jobKey);
    }

    private JobKey getJobKey(Long jobId) {
        return JobKey.jobKey("job_" + jobId, SysJobConstants.DEFAULT_JOB_GROUP);
    }

    private TriggerKey getTriggerKey(Long jobId) {
        return TriggerKey.triggerKey("trigger_" + jobId, SysJobConstants.DEFAULT_JOB_GROUP);
    }
}
