package org.example.backend.quartz.registry;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.extern.slf4j.Slf4j;
import org.example.backend.quartz.constant.SysJobConstants;
import org.example.backend.quartz.entity.SysJobEntity;
import org.example.backend.quartz.mapper.SysJobMapper;
import org.example.backend.quartz.task.Task;
import org.example.backend.quartz.task.TaskInfo;
import org.springframework.context.ApplicationContext;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import javax.annotation.Resource;
import java.util.Date;
import java.util.Map;

@Slf4j
@Component
public class TaskRegistry {

    @Resource
    private ApplicationContext applicationContext;

    @Resource
    private SysJobMapper sysJobMapper;

    @PostConstruct
    public void registerTasks() {
        Map<String, Task> taskMap = applicationContext.getBeansOfType(Task.class);
        int annotatedCount = 0;
        int insertedCount = 0;

        for (Map.Entry<String, Task> entry : taskMap.entrySet()) {
            String beanName = entry.getKey();
            Task task = entry.getValue();
            TaskInfo taskInfo = task.getClass().getAnnotation(TaskInfo.class);
            if (taskInfo == null) {
                continue;
            }
            annotatedCount++;

            SysJobEntity existing = sysJobMapper.selectOne(
                    new LambdaQueryWrapper<SysJobEntity>().eq(SysJobEntity::getBeanName, beanName)
            );
            if (existing != null) {
                continue;
            }

            Date now = new Date();
            SysJobEntity entity = new SysJobEntity()
                    .setBeanName(beanName)
                    .setJobName(taskInfo.name())
                    .setDescription(taskInfo.description())
                    .setJobGroup(SysJobConstants.DEFAULT_JOB_GROUP)
                    .setCronExpression(SysJobConstants.UNCONFIGURED_CRON_EXPRESSION)
                    .setStatus(SysJobConstants.RUN_IDLE)
                    .setEnabled(SysJobConstants.ENABLED_NO)
                    .setCreateTime(now)
                    .setUpdateTime(now);

            sysJobMapper.insert(entity);
            insertedCount++;
        }

        log.info("扫描 Task Bean 完成：共 {} 个，带 @TaskInfo {} 个，新写入 sys_job {} 个",
                taskMap.size(), annotatedCount, insertedCount);
    }
}
