package org.example.backend.quartz.task;

import org.springframework.stereotype.Component;

@Component
@TaskInfo(
        name = "系统汇报",
        description = "汇报系统状况"
)
public class SysReportTask implements Task {

    @Override
    public void execute() {
        sysReport();
    }

    public void sysReport() {
        System.out.println("[SysReportTask] 系统汇报任务执行中：正在汇总系统状况...");
        System.out.println("[SysReportTask] 系统汇报完成。");
    }
}
