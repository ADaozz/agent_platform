package org.example.backend.quartz.service;

import com.baomidou.mybatisplus.extension.service.IService;
import org.example.backend.common.vo.PageResultVO;
import org.example.backend.quartz.dto.SysJobQueryDTO;
import org.example.backend.quartz.dto.SysJobUpdateDTO;
import org.example.backend.quartz.entity.SysJobEntity;
import org.example.backend.quartz.vo.SysJobVO;

public interface SysJobService extends IService<SysJobEntity> {

    PageResultVO<SysJobVO> listSysJob(SysJobQueryDTO dto);

    void updateSysJob(SysJobUpdateDTO dto);

    void changeJobEnabled(Long jobId, String enabled);

    void runJobOnce(Long jobId);

    SysJobEntity getJobOrThrow(Long jobId);
}
