package org.example.backend.asset.host.infrastructure.persistence;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import org.example.backend.asset.app.entity.VmAppEntity;
import org.example.backend.asset.app.mapper.VmAppMapper;
import org.example.backend.asset.host.domain.model.VmHost;
import org.example.backend.asset.host.domain.repository.VmHostRepository;
import org.example.backend.asset.host.entity.VmHostEntity;
import org.example.backend.asset.host.mapper.VmHostMapper;
import org.springframework.stereotype.Repository;
import org.springframework.util.StringUtils;

import javax.annotation.Resource;
import java.util.Date;
import java.util.Optional;

@Repository
public class VmHostRepositoryImpl implements VmHostRepository {

    @Resource
    private VmHostMapper vmHostMapper;

    @Resource
    private VmAppMapper vmAppMapper;

    @Override
    public Optional<VmHost> findById(String hostId) {
        VmHostEntity entity = vmHostMapper.selectById(hostId);
        return Optional.ofNullable(VmHostConverter.toDomain(entity));
    }

    @Override
    public boolean existsByHostNameExcept(String hostName, String excludeHostId) {
        if (!StringUtils.hasText(hostName)) {
            return false;
        }
        LambdaQueryWrapper<VmHostEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(VmHostEntity::getHostName, hostName);
        VmHostEntity duplicate = vmHostMapper.selectOne(wrapper);
        return duplicate != null && !duplicate.getHostId().equals(excludeHostId);
    }

    @Override
    public void save(VmHost host, boolean syncAppIp) {
        VmHostEntity entity = VmHostConverter.toEntity(host);
        vmHostMapper.updateById(entity);
        if (syncAppIp) {
            LambdaUpdateWrapper<VmAppEntity> update = new LambdaUpdateWrapper<>();
            update.eq(VmAppEntity::getHostId, host.getHostId())
                    .set(VmAppEntity::getVmIp, host.getVmIp())
                    .set(VmAppEntity::getUpdateTime, new Date());
            vmAppMapper.update(null, update);
        }
    }
}
