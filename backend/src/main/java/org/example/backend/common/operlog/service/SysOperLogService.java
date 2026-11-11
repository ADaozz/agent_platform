package org.example.backend.common.operlog.service;

import org.example.backend.common.operlog.entity.SysOperLogEntity;

public interface SysOperLogService {

    void saveAsync(SysOperLogEntity operLog);
}
