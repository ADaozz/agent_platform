package org.example.backend.asset.port;

import java.util.Collection;
import java.util.Map;

/**
 * Asset 上下文查询 IAM 用户展示信息的防腐层端口。
 */
public interface UserQueryPort {

    String getUserName(Long userId);

    Map<Long, String> getUserNames(Collection<Long> userIds);
}
