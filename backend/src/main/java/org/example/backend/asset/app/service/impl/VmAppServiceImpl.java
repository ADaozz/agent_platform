package org.example.backend.asset.app.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.example.backend.asset.app.application.VmAppApplicationService;
import org.example.backend.asset.app.dto.VmAppQueryDTO;
import org.example.backend.asset.app.dto.VmAppUpdateDTO;
import org.example.backend.asset.app.entity.VmAppEntity;
import org.example.backend.asset.app.mapper.VmAppMapper;
import org.example.backend.asset.app.service.VmAppService;
import org.example.backend.asset.app.vo.VmAppVO;
import org.example.backend.common.exception.BusinessException;
import org.example.backend.common.exception.Module;
import org.example.backend.common.vo.PageResultVO;
import org.example.backend.security.context.LoginUserUtils;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import javax.annotation.Resource;
import java.util.Collections;
import java.util.List;
import java.util.stream.Collectors;

@Service
public class VmAppServiceImpl extends ServiceImpl<VmAppMapper, VmAppEntity> implements VmAppService {

    @Resource
    private VmAppApplicationService vmAppApplicationService;

    @Override
    // 分页查询应用列表
    public PageResultVO<VmAppVO> listVmApp(VmAppQueryDTO dto) {
        if (StringUtils.hasText(dto.getAppId())) {
            VmAppVO vo = toVmAppVO(getVmAppOrThrow(dto.getAppId()));
            return new PageResultVO<>(1, Collections.singletonList(vo));
        }

        LambdaQueryWrapper<VmAppEntity> wrapper = buildQueryWrapper(dto);
        int pageNum = dto.getPageNum() != null ? dto.getPageNum() : 1;
        int pageSize = dto.getPageSize() != null ? dto.getPageSize() : 10;
        Page<VmAppEntity> page = page(new Page<>(pageNum, pageSize), wrapper);

        List<VmAppVO> rows = page.getRecords().stream()
                .map(this::toVmAppVO)
                .collect(Collectors.toList());
        return new PageResultVO<>(page.getTotal(), rows);
    }

    @Override
    // 更新应用信息
    public void updateVmApp(VmAppUpdateDTO dto) {
        Long userId = LoginUserUtils.getUserId();
        if (userId == null) {
            throw new BusinessException(Module.ModuleType.AUTH, "未登录", null);
        }
        vmAppApplicationService.updateVmApp(dto, userId);
    }

    // 获取应用或抛出不存在异常
    private VmAppEntity getVmAppOrThrow(String appId) {
        VmAppEntity app = getById(appId);
        if (app == null) {
            throw new BusinessException(Module.ModuleType.ASSET, "应用不存在", null);
        }
        return app;
    }

    // 构建应用查询条件
    private LambdaQueryWrapper<VmAppEntity> buildQueryWrapper(VmAppQueryDTO dto) {
        LambdaQueryWrapper<VmAppEntity> wrapper = new LambdaQueryWrapper<>();
        if (StringUtils.hasText(dto.getAppName())) {
            wrapper.like(VmAppEntity::getAppName, dto.getAppName());
        }
        if (StringUtils.hasText(dto.getHostId())) {
            wrapper.eq(VmAppEntity::getHostId, dto.getHostId());
        }
        if (StringUtils.hasText(dto.getVmIp())) {
            wrapper.like(VmAppEntity::getVmIp, dto.getVmIp());
        }
        if (StringUtils.hasText(dto.getAppStatus())) {
            wrapper.eq(VmAppEntity::getAppStatus, dto.getAppStatus());
        }
        wrapper.orderByDesc(VmAppEntity::getCreateTime);
        return wrapper;
    }

    // 将应用实体转换为VO
    private VmAppVO toVmAppVO(VmAppEntity entity) {
        VmAppVO vo = new VmAppVO();
        vo.setAppId(entity.getAppId());
        vo.setAppName(entity.getAppName());
        vo.setHostId(entity.getHostId());
        vo.setVmIp(entity.getVmIp());
        vo.setDeployPath(entity.getDeployPath());
        vo.setAppStatus(entity.getAppStatus());
        vo.setCreateTime(entity.getCreateTime());
        vo.setUpdateTime(entity.getUpdateTime());
        return vo;
    }
}
