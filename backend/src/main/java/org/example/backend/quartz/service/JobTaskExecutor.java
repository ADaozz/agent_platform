package org.example.backend.quartz.service;

import lombok.extern.slf4j.Slf4j;
import org.example.backend.common.exception.BusinessException;
import org.example.backend.common.exception.Module;
import org.example.backend.quartz.constant.SysJobConstants;
import org.example.backend.quartz.entity.SysJobEntity;
import org.example.backend.quartz.entity.SysJobLogEntity;
import org.example.backend.quartz.mapper.SysJobLogMapper;
import org.example.backend.quartz.mapper.SysJobMapper;
import org.example.backend.quartz.task.Task;
import org.springframework.context.ApplicationContext;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import javax.annotation.Resource;
import java.util.Date;

@Slf4j
@Service
public class JobTaskExecutor {

    private static final String LOG_SUCCESS = "0";
    private static final String LOG_FAILURE = "1";

    @Resource
    private ApplicationContext applicationContext;

    @Resource
    private SysJobMapper sysJobMapper;

    @Resource
    private SysJobLogMapper sysJobLogMapper;

    /**
     * @param manual true=接口手动触发，失败时抛业务异常；false=Cron 调度，失败仅记日志
     */
    public void execute(SysJobEntity job, boolean manual) {
        Date startTime = new Date();
        SysJobLogEntity logEntity = new SysJobLogEntity()
                .setJobId(job.getJobId())
                .setJobName(job.getJobName())
                .setStartTime(startTime);

        markRunning(job.getJobId());

        try {
            Task task = applicationContext.getBean(job.getBeanName(), Task.class);
            task.execute();
            logEntity.setStatus(LOG_SUCCESS);
            logEntity.setMessage(manual ? "手动执行成功" : "调度执行成功");
            markFinished(job.getJobId(), SysJobConstants.RUN_SUCCESS);
        } catch (Exception e) {
            log.error("定时任务执行失败, jobId={}, beanName={}, manual={}",
                    job.getJobId(), job.getBeanName(), manual, e);
            logEntity.setStatus(LOG_FAILURE);
            logEntity.setMessage(truncateMessage(e.getMessage()));
            markFinished(job.getJobId(), SysJobConstants.RUN_FAILURE);
            if (manual) {
                throw new BusinessException(Module.ModuleType.QUARTZ, "任务执行失败: " + e.getMessage(), e);
            }
        } finally {
            logEntity.setEndTime(new Date());
            sysJobLogMapper.insert(logEntity);
        }
    }

    private void markRunning(Long jobId) {
        SysJobEntity update = new SysJobEntity()
                .setJobId(jobId)
                .setStatus(SysJobConstants.RUN_RUNNING)
                .setUpdateTime(new Date());
        sysJobMapper.updateById(update);
    }

    private void markFinished(Long jobId, String status) {
        SysJobEntity update = new SysJobEntity()
                .setJobId(jobId)
                .setStatus(status)
                .setUpdateTime(new Date());
        sysJobMapper.updateById(update);
    }

    private String truncateMessage(String message) {
        if (!StringUtils.hasText(message)) {
            return "执行失败";
        }
        return message.length() > 2000 ? message.substring(0, 2000) : message;
    }
}
