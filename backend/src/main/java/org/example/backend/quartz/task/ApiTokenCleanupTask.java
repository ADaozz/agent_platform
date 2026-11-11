package org.example.backend.quartz.task;

import lombok.extern.slf4j.Slf4j;
import org.example.backend.api.service.ApiTokenService;
import org.springframework.stereotype.Component;

import javax.annotation.Resource;

@Component
@TaskInfo(
        name = "API Token 清理",
        description = "清除 API 开放接口中状态为已吊销的凭证"
)
@Slf4j
public class ApiTokenCleanupTask implements Task {

    @Resource
    private ApiTokenService apiTokenService;

    @Override
    public void execute() {
        int removed = apiTokenService.purgeRevokedTokens();
        log.info("[ApiTokenCleanupTask] 已清除 {} 条已吊销 API Token", removed);
    }
}
