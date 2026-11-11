package org.example.backend.asset.host.domain.model;

import org.example.backend.common.exception.BusinessException;
import org.example.backend.common.exception.Module;
import org.springframework.util.StringUtils;

import java.util.Date;

/**
 * 虚机聚合根：生命周期、归属校验、改 IP 与关联应用同步在同一边界内。
 */
public class VmHost {

    private String hostId;
    private String hostName;
    private String osType;
    private String osVersion;
    private String vmIp;
    private Integer cpuCores;
    private Integer memoryGb;
    private Integer diskGb;
    private String physicalHostIp;
    private VmLifecycle lifecycle;
    private Long ownerUserId;
    private String networkZone;
    private String env;
    private String remark;
    private Date createTime;
    private Date updateTime;

    public void assertOwnedBy(Long operatorUserId) {
        if (operatorUserId == null) {
            throw new BusinessException(Module.ModuleType.AUTH, "未登录", null);
        }
        if (ownerUserId == null || !ownerUserId.equals(operatorUserId)) {
            throw new BusinessException(Module.ModuleType.ASSET, "无权修改该虚机", null);
        }
    }

    public void assertMutable() {
        if (lifecycle != null && lifecycle.isTerminal()) {
            throw new BusinessException(Module.ModuleType.ASSET, "虚机已销毁，不可修改", null);
        }
    }

    /** 归属人校验 + 虚机未销毁，供其下应用变更使用 */
    public void assertOperatorCanManageApps(Long operatorUserId) {
        assertOwnedBy(operatorUserId);
        if (lifecycle != null && lifecycle.isTerminal()) {
            throw new BusinessException(Module.ModuleType.ASSET, "虚机已销毁，不可修改其应用", null);
        }
    }

    public void applyUpdate(VmHostUpdateCommand command, boolean hostNameTaken) {
        assertMutable();
        if (hostNameTaken) {
            throw new BusinessException(Module.ModuleType.ASSET, "虚机名称已存在", null);
        }
        if (StringUtils.hasText(command.getLifecycleStatus())) {
            try {
                lifecycle = lifecycle.transitionTo(command.getLifecycleStatus());
            } catch (IllegalArgumentException e) {
                throw new BusinessException(Module.ModuleType.ASSET,
                        "非法生命周期流转: " + lifecycle.getValue() + " -> " + command.getLifecycleStatus(), null);
            }
        }
        hostName = command.getHostName();
        osType = command.getOsType();
        osVersion = command.getOsVersion();
        vmIp = command.getVmIp();
        cpuCores = command.getCpuCores();
        memoryGb = command.getMemoryGb();
        diskGb = command.getDiskGb();
        physicalHostIp = command.getPhysicalHostIp();
        networkZone = command.getNetworkZone();
        env = command.getEnv();
        remark = command.getRemark();
        updateTime = new Date();
    }

    public boolean shouldSyncAppIp(String newIp) {
        return StringUtils.hasText(newIp) && !newIp.equals(vmIp);
    }

    public String getHostId() {
        return hostId;
    }

    public void setHostId(String hostId) {
        this.hostId = hostId;
    }

    public String getHostName() {
        return hostName;
    }

    public String getOsType() {
        return osType;
    }

    public String getOsVersion() {
        return osVersion;
    }

    public String getVmIp() {
        return vmIp;
    }

    public Integer getCpuCores() {
        return cpuCores;
    }

    public Integer getMemoryGb() {
        return memoryGb;
    }

    public Integer getDiskGb() {
        return diskGb;
    }

    public String getPhysicalHostIp() {
        return physicalHostIp;
    }

    public VmLifecycle getLifecycle() {
        return lifecycle;
    }

    public String getLifecycleStatus() {
        return lifecycle != null ? lifecycle.getValue() : null;
    }

    public Long getOwnerUserId() {
        return ownerUserId;
    }

    public String getNetworkZone() {
        return networkZone;
    }

    public String getEnv() {
        return env;
    }

    public String getRemark() {
        return remark;
    }

    public Date getCreateTime() {
        return createTime;
    }

    public Date getUpdateTime() {
        return updateTime;
    }

    public void setHostName(String hostName) {
        this.hostName = hostName;
    }

    public void setOsType(String osType) {
        this.osType = osType;
    }

    public void setOsVersion(String osVersion) {
        this.osVersion = osVersion;
    }

    public void setVmIp(String vmIp) {
        this.vmIp = vmIp;
    }

    public void setCpuCores(Integer cpuCores) {
        this.cpuCores = cpuCores;
    }

    public void setMemoryGb(Integer memoryGb) {
        this.memoryGb = memoryGb;
    }

    public void setDiskGb(Integer diskGb) {
        this.diskGb = diskGb;
    }

    public void setPhysicalHostIp(String physicalHostIp) {
        this.physicalHostIp = physicalHostIp;
    }

    public void setLifecycle(VmLifecycle lifecycle) {
        this.lifecycle = lifecycle;
    }

    public void setOwnerUserId(Long ownerUserId) {
        this.ownerUserId = ownerUserId;
    }

    public void setNetworkZone(String networkZone) {
        this.networkZone = networkZone;
    }

    public void setEnv(String env) {
        this.env = env;
    }

    public void setRemark(String remark) {
        this.remark = remark;
    }

    public void setCreateTime(Date createTime) {
        this.createTime = createTime;
    }

    public void setUpdateTime(Date updateTime) {
        this.updateTime = updateTime;
    }
}
