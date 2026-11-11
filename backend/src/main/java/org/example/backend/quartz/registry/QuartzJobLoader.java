package org.example.backend.quartz.registry;

import lombok.extern.slf4j.Slf4j;
import org.example.backend.quartz.service.QuartzSchedulerService;
import org.springframework.context.ApplicationListener;
import org.springframework.context.event.ContextRefreshedEvent;
import org.springframework.stereotype.Component;

import javax.annotation.Resource;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * 应用启动并完成 Task 注册后，将已启用任务加载到 Quartz Scheduler。
 */
@Slf4j
@Component
public class QuartzJobLoader implements ApplicationListener<ContextRefreshedEvent> {

    private final AtomicBoolean loaded = new AtomicBoolean(false);

    @Resource
    private QuartzSchedulerService quartzSchedulerService;

    @Override
    public void onApplicationEvent(ContextRefreshedEvent event) {
        if (!loaded.compareAndSet(false, true)) {
            return;
        }
        log.info("从 sys_job 加载已启用的定时任务到 Quartz Scheduler...");
        quartzSchedulerService.loadAvailableTasks();
    }
}
