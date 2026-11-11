package org.example.backend.asset.app.application;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import org.example.backend.asset.app.dto.VmAppUpdateDTO;
import org.example.backend.asset.app.entity.VmAppEntity;
import org.example.backend.asset.app.mapper.VmAppMapper;
import org.example.backend.asset.host.domain.model.VmHost;
import org.example.backend.asset.host.domain.repository.VmHostRepository;
import org.example.backend.common.exception.BusinessException;
import org.example.backend.common.exception.Module;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.annotation.Resource;
import java.util.Date;

@Service
public class VmAppApplicationService {

    @Resource
    private VmAppMapper vmAppMapper;

    @Resource
    private VmHostRepository vmHostRepository;

    @Transactional(rollbackFor = Exception.class)
    public void updateVmApp(VmAppUpdateDTO dto, Long operatorUserId) {
        VmAppEntity app = vmAppMapper.selectById(dto.getAppId());
        if (app == null) {
            throw new BusinessException(Module.ModuleType.ASSET, "应用不存在", null);
        }

        VmHost host = vmHostRepository.findById(app.getHostId())
                .orElseThrow(() -> new BusinessException(Module.ModuleType.ASSET, "虚机不存在", null));
        host.assertOperatorCanManageApps(operatorUserId);

        LambdaQueryWrapper<VmAppEntity> dupWrapper = new LambdaQueryWrapper<>();
        dupWrapper.eq(VmAppEntity::getHostId, app.getHostId())
                .eq(VmAppEntity::getDeployPath, dto.getDeployPath());
        VmAppEntity duplicate = vmAppMapper.selectOne(dupWrapper);
        if (duplicate != null && !duplicate.getAppId().equals(dto.getAppId())) {
            throw new BusinessException(Module.ModuleType.ASSET, "同虚机下部署路径已存在", null);
        }

        app.setAppName(dto.getAppName());
        app.setDeployPath(dto.getDeployPath());
        app.setAppStatus(dto.getAppStatus());
        app.setUpdateTime(new Date());
        vmAppMapper.updateById(app);
    }
}
