package org.example.backend.asset.host.application;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import org.example.backend.asset.host.dto.VmHostQueryDTO;
import org.example.backend.asset.host.entity.VmHostEntity;
import org.example.backend.asset.host.mapper.VmHostMapper;
import org.example.backend.asset.host.vo.VmHostVO;
import org.example.backend.asset.port.UserQueryPort;
import org.example.backend.common.exception.BusinessException;
import org.example.backend.common.exception.Module;
import org.example.backend.common.vo.OptionVO;
import org.example.backend.common.vo.PageResultVO;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import javax.annotation.Resource;
import java.util.Collections;
import java.util.List;
import java.util.stream.Collectors;

/**
 * 虚机读模型查询，与写路径聚合分离。
 */
@Service
public class VmHostQueryService {

    @Resource
    private VmHostMapper vmHostMapper;

    @Resource
    private UserQueryPort userQueryPort;

    public PageResultVO<VmHostVO> listVmHost(VmHostQueryDTO dto) {
        if (StringUtils.hasText(dto.getHostId())) {
            VmHostEntity entity = vmHostMapper.selectById(dto.getHostId());
            if (entity == null) {
                throw new BusinessException(Module.ModuleType.ASSET, "虚机不存在", null);
            }
            return new PageResultVO<>(1, Collections.singletonList(toVo(entity)));
        }

        LambdaQueryWrapper<VmHostEntity> wrapper = buildQueryWrapper(dto);
        int pageNum = dto.getPageNum() != null ? dto.getPageNum() : 1;
        int pageSize = dto.getPageSize() != null ? dto.getPageSize() : 10;
        Page<VmHostEntity> page = vmHostMapper.selectPage(new Page<>(pageNum, pageSize), wrapper);

        List<VmHostVO> rows = page.getRecords().stream()
                .map(this::toVo)
                .collect(Collectors.toList());
        return new PageResultVO<>(page.getTotal(), rows);
    }

    private LambdaQueryWrapper<VmHostEntity> buildQueryWrapper(VmHostQueryDTO dto) {
        LambdaQueryWrapper<VmHostEntity> wrapper = new LambdaQueryWrapper<>();
        if (StringUtils.hasText(dto.getHostName())) {
            wrapper.like(VmHostEntity::getHostName, dto.getHostName());
        }
        if (StringUtils.hasText(dto.getVmIp())) {
            wrapper.like(VmHostEntity::getVmIp, dto.getVmIp());
        }
        if (StringUtils.hasText(dto.getLifecycleStatus())) {
            wrapper.eq(VmHostEntity::getLifecycleStatus, dto.getLifecycleStatus());
        }
        if (dto.getOwnerUserId() != null) {
            wrapper.eq(VmHostEntity::getOwnerUserId, dto.getOwnerUserId());
        }
        if (StringUtils.hasText(dto.getNetworkZone())) {
            wrapper.eq(VmHostEntity::getNetworkZone, dto.getNetworkZone());
        }
        if (StringUtils.hasText(dto.getEnv())) {
            wrapper.eq(VmHostEntity::getEnv, dto.getEnv());
        }
        wrapper.orderByDesc(VmHostEntity::getCreateTime);
        return wrapper;
    }

    private VmHostVO toVo(VmHostEntity entity) {
        VmHostVO vo = new VmHostVO();
        vo.setHostId(entity.getHostId());
        vo.setHostName(entity.getHostName());
        vo.setOsType(entity.getOsType());
        vo.setOsVersion(entity.getOsVersion());
        vo.setVmIp(entity.getVmIp());
        vo.setCpuCores(entity.getCpuCores());
        vo.setMemoryGb(entity.getMemoryGb());
        vo.setDiskGb(entity.getDiskGb());
        vo.setPhysicalHostIp(entity.getPhysicalHostIp());
        vo.setLifecycleStatus(entity.getLifecycleStatus());
        vo.setNetworkZone(entity.getNetworkZone());
        vo.setEnv(entity.getEnv());
        vo.setRemark(entity.getRemark());
        vo.setCreateTime(entity.getCreateTime());
        vo.setUpdateTime(entity.getUpdateTime());
        if (entity.getOwnerUserId() != null) {
            String label = userQueryPort.getUserName(entity.getOwnerUserId());
            vo.setOwner(new OptionVO(entity.getOwnerUserId(), label));
        }
        return vo;
    }
}
