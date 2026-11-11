package org.example.backend.asset.host.domain.repository;

import org.example.backend.asset.host.domain.model.VmHost;

import java.util.Optional;

public interface VmHostRepository {

    Optional<VmHost> findById(String hostId);

    boolean existsByHostNameExcept(String hostName, String excludeHostId);

    void save(VmHost host, boolean syncAppIp);
}
