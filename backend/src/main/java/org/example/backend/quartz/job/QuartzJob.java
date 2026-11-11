package org.example.backend.quartz.job;

import lombok.extern.slf4j.Slf4j;
import org.example.backend.quartz.constant.SysJobConstants;
import org.example.backend.quartz.entity.SysJobEntity;
import org.example.backend.quartz.mapper.SysJobMapper;
import org.example.backend.quartz.service.JobTaskExecutor;
import org.quartz.DisallowConcurrentExecution;
import org.quartz.Job;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.springframework.stereotype.Component;

import javax.annotation.Resource;

@Slf4j
@Component
@DisallowConcurrentExecution
public class QuartzJob implements Job {

    @Resource
    private JobTaskExecutor jobTaskExecutor;

    @Resource
    private SysJobMapper sysJobMapper;

    @Override
    public void execute(JobExecutionContext context) throws JobExecutionException {
        Long jobId = context.getMergedJobDataMap().getLong("jobId");
        SysJobEntity job = sysJobMapper.selectById(jobId);
        if (job == null) {
            log.warn("Quartz 触发时任务不存在: jobId={}", jobId);
            return;
        }
        if (!SysJobConstants.ENABLED_YES.equals(job.getEnabled())) {
            log.warn("Quartz 触发时任务已停用: jobId={}", jobId);
            return;
        }

        try {
            jobTaskExecutor.execute(job, false);
        } catch (Exception e) {
            throw new JobExecutionException(e);
        }
    }
}
