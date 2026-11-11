package org.example.backend.asset.host.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.example.backend.asset.host.application.VmHostApplicationService;
import org.example.backend.asset.host.application.VmHostQueryService;
import org.example.backend.asset.host.dto.VmHostQueryDTO;
import org.example.backend.asset.host.dto.VmHostUpdateDTO;
import org.example.backend.asset.host.entity.VmHostEntity;
import org.example.backend.asset.host.mapper.VmHostMapper;
import org.example.backend.asset.host.service.VmHostService;
import org.example.backend.asset.host.vo.VmHostVO;
import org.example.backend.common.exception.BusinessException;
import org.example.backend.common.exception.Module;
import org.example.backend.common.vo.PageResultVO;
import org.example.backend.security.context.LoginUserUtils;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;

@Service
public class VmHostServiceImpl extends ServiceImpl<VmHostMapper, VmHostEntity> implements VmHostService {

    @Resource
    private VmHostApplicationService vmHostApplicationService;

    @Resource
    private VmHostQueryService vmHostQueryService;

    @Override
    // 分页查询虚机列表
    public PageResultVO<VmHostVO> listVmHost(VmHostQueryDTO dto) {
        return vmHostQueryService.listVmHost(dto);
    }

    @Override
    // 更新虚机信息
    public void updateVmHost(VmHostUpdateDTO dto) {
        Long userId = LoginUserUtils.getUserId();
        if (userId == null) {
            throw new BusinessException(Module.ModuleType.AUTH, "未登录", null);
        }
        vmHostApplicationService.updateVmHost(dto, userId);
    }
}
