package org.example.backend.asset.host.infrastructure.persistence;

import org.example.backend.asset.host.domain.model.VmHost;
import org.example.backend.asset.host.domain.model.VmLifecycle;
import org.example.backend.asset.host.entity.VmHostEntity;
import org.springframework.util.StringUtils;

final class VmHostConverter {

    private VmHostConverter() {
    }

    static VmHost toDomain(VmHostEntity entity) {
        if (entity == null) {
            return null;
        }
        VmHost host = new VmHost();
        host.setHostId(entity.getHostId());
        host.setHostName(entity.getHostName());
        host.setOsType(entity.getOsType());
        host.setOsVersion(entity.getOsVersion());
        host.setVmIp(entity.getVmIp());
        host.setCpuCores(entity.getCpuCores());
        host.setMemoryGb(entity.getMemoryGb());
        host.setDiskGb(entity.getDiskGb());
        host.setPhysicalHostIp(entity.getPhysicalHostIp());
        host.setLifecycle(StringUtils.hasText(entity.getLifecycleStatus())
                ? VmLifecycle.of(entity.getLifecycleStatus())
                : VmLifecycle.of(VmLifecycle.CREATING));
        host.setOwnerUserId(entity.getOwnerUserId());
        host.setNetworkZone(entity.getNetworkZone());
        host.setEnv(entity.getEnv());
        host.setRemark(entity.getRemark());
        host.setCreateTime(entity.getCreateTime());
        host.setUpdateTime(entity.getUpdateTime());
        return host;
    }

    static VmHostEntity toEntity(VmHost host) {
        if (host == null) {
            return null;
        }
        VmHostEntity entity = new VmHostEntity();
        entity.setHostId(host.getHostId());
        entity.setHostName(host.getHostName());
        entity.setOsType(host.getOsType());
        entity.setOsVersion(host.getOsVersion());
        entity.setVmIp(host.getVmIp());
        entity.setCpuCores(host.getCpuCores());
        entity.setMemoryGb(host.getMemoryGb());
        entity.setDiskGb(host.getDiskGb());
        entity.setPhysicalHostIp(host.getPhysicalHostIp());
        entity.setLifecycleStatus(host.getLifecycleStatus());
        entity.setOwnerUserId(host.getOwnerUserId());
        entity.setNetworkZone(host.getNetworkZone());
        entity.setEnv(host.getEnv());
        entity.setRemark(host.getRemark());
        entity.setCreateTime(host.getCreateTime());
        entity.setUpdateTime(host.getUpdateTime());
        return entity;
    }
}
