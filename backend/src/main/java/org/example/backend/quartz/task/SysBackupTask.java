package org.example.backend.quartz.task;

import org.springframework.stereotype.Component;

@Component
@TaskInfo(
        name = "系统备份",
        description = "备份系统数据"
)
public class SysBackupTask implements Task {

    @Override
    public void execute() {
        sysBackup();
    }

    public void sysBackup() {
        System.out.println("[SysBackupTask] 系统备份任务执行中：正在备份系统数据...");
        System.out.println("[SysBackupTask] 系统备份完成。");
    }
}