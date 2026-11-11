package org.example.backend.asset.host.application;

import org.example.backend.asset.host.domain.model.VmHost;
import org.example.backend.asset.host.domain.model.VmHostUpdateCommand;
import org.example.backend.asset.host.domain.repository.VmHostRepository;
import org.example.backend.asset.host.dto.VmHostUpdateDTO;
import org.example.backend.common.exception.BusinessException;
import org.example.backend.common.exception.Module;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.annotation.Resource;

@Service
public class VmHostApplicationService {

    @Resource
    private VmHostRepository vmHostRepository;

    @Transactional(rollbackFor = Exception.class)
    public void updateVmHost(VmHostUpdateDTO dto, Long operatorUserId) {
        VmHost host = vmHostRepository.findById(dto.getHostId())
                .orElseThrow(() -> new BusinessException(Module.ModuleType.ASSET, "虚机不存在", null));

        host.assertOwnedBy(operatorUserId);

        boolean hostNameTaken = vmHostRepository.existsByHostNameExcept(dto.getHostName(), dto.getHostId());
        VmHostUpdateCommand command = toCommand(dto);
        boolean syncAppIp = host.shouldSyncAppIp(dto.getVmIp());

        host.applyUpdate(command, hostNameTaken);
        vmHostRepository.save(host, syncAppIp);
    }

    private VmHostUpdateCommand toCommand(VmHostUpdateDTO dto) {
        return VmHostUpdateCommand.builder()
                .hostName(dto.getHostName())
                .osType(dto.getOsType())
                .osVersion(dto.getOsVersion())
                .vmIp(dto.getVmIp())
                .cpuCores(dto.getCpuCores())
                .memoryGb(dto.getMemoryGb())
                .diskGb(dto.getDiskGb())
                .physicalHostIp(dto.getPhysicalHostIp())
                .lifecycleStatus(dto.getLifecycleStatus())
                .networkZone(dto.getNetworkZone())
                .env(dto.getEnv())
                .remark(dto.getRemark())
                .build();
    }
}
