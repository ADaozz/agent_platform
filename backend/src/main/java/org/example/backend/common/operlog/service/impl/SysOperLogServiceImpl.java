package org.example.backend.common.operlog.service.impl;

import lombok.extern.slf4j.Slf4j;
import org.example.backend.common.operlog.entity.SysOperLogEntity;
import org.example.backend.common.operlog.mapper.SysOperLogMapper;
import org.example.backend.common.operlog.service.SysOperLogService;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;

@Service
@Slf4j
public class SysOperLogServiceImpl implements SysOperLogService {

    @Resource
    private SysOperLogMapper sysOperLogMapper;

    @Async("operLogExecutor")
    @Override
    // 异步保存操作日志
    public void saveAsync(SysOperLogEntity operLog) {
        try {
            sysOperLogMapper.insert(operLog);
        } catch (Exception e) {
            log.warn("操作日志落库失败 title={} method={}", operLog.getTitle(), operLog.getMethod(), e);
        }
    }
}
