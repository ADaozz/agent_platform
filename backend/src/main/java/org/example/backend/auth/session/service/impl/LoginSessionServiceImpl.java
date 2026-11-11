package org.example.backend.auth.session.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.apache.shiro.authc.AuthenticationException;
import org.example.backend.auth.session.dto.LoginSessionQueryDTO;
import org.example.backend.auth.session.entity.LoginSessionEntity;
import org.example.backend.auth.session.mapper.LoginSessionMapper;
import org.example.backend.auth.session.service.LoginSessionService;
import org.example.backend.auth.session.util.UserAgentUtils;
import org.example.backend.auth.session.vo.LoginSessionVO;
import org.example.backend.common.exception.BusinessException;
import org.example.backend.common.exception.Module;
import org.example.backend.common.vo.PageResultVO;
import org.example.backend.system.user.entity.SysUserEntity;
import org.example.backend.system.user.service.SysUserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import org.example.backend.auth.session.constant.SessionRedisKeys;
import org.springframework.dao.DataAccessException;
import org.springframework.data.redis.RedisConnectionFailureException;
import org.springframework.transaction.annotation.Transactional;

import java.util.concurrent.TimeUnit;

import javax.annotation.Resource;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
public class LoginSessionServiceImpl extends ServiceImpl<LoginSessionMapper, LoginSessionEntity>
        implements LoginSessionService {

    private static final String STATUS_ACTIVE = "0";
    private static final String STATUS_REVOKED = "1";

    @Resource
    private StringRedisTemplate stringRedisTemplate;

    @Resource
    private LoginSessionMapper loginSessionMapper;

    @Autowired
    private SysUserService sysUserService;

    @Value("${jwt.expire}")
    private long jwtExpireSeconds;

    @Override
    // 创建登录会话并缓存到Redis
    public String createSession(Long userId, String loginIp, String userAgent, String loginType) {
        String sessionId = UUID.randomUUID().toString().replace("-", "");
        LoginSessionEntity entity = new LoginSessionEntity();
        entity.setSessionId(sessionId);
        entity.setUserId(userId);
        entity.setDeviceName(UserAgentUtils.parseDeviceName(userAgent));
        entity.setLoginIp(loginIp);
        entity.setUserAgent(StringUtils.hasText(userAgent) ? truncate(userAgent, 512) : null);
        entity.setLoginTime(new Date());
        entity.setStatus(STATUS_ACTIVE);
        entity.setLoginType(StringUtils.hasText(loginType) ? loginType : "0");
        save(entity);
        cacheActiveSession(sessionId, userId);
        return sessionId;
    }

    @Override
    // 单点登录：撤销旧会话后创建新会话
    public String createSingleLoginSession(Long userId, String loginIp, String userAgent, String loginType) {
        revokeAllActiveSessions(userId);
        return createSession(userId, loginIp, userAgent, loginType);
    }

    @Override
    // 吊销指定登录会话
    public void revokeSession(String sessionId) {
        if (!StringUtils.hasText(sessionId)) {
            return;
        }
        LoginSessionEntity entity = loginSessionMapper.selectById(sessionId);
        stringRedisTemplate.delete(
                SessionRedisKeys.session(sessionId)
        );
        if (entity != null && entity.getUserId() != null) {
            String userSessionKey =
                    SessionRedisKeys.userSession(entity.getUserId());

            String currentSessionId =
                    stringRedisTemplate.opsForValue()
                            .get(userSessionKey);

            if (sessionId.equals(currentSessionId)) {
                stringRedisTemplate.delete(userSessionKey);
            }
        }


        LambdaUpdateWrapper<LoginSessionEntity> wrapper = new LambdaUpdateWrapper<>();
        wrapper.eq(LoginSessionEntity::getSessionId, sessionId)
                .eq(LoginSessionEntity::getStatus, STATUS_ACTIVE)
                .set(LoginSessionEntity::getStatus, STATUS_REVOKED)
                .set(LoginSessionEntity::getRevokeTime, new Date());
        update(wrapper);
    }

    @Override
    // 吊销用户所有活跃会话
    public void revokeAllActiveSessions(Long userId) {
        if (userId == null) {
            return;
        }

        String userSessionKey = SessionRedisKeys.userSession(userId);

        String oldSessionId = stringRedisTemplate.opsForValue().get(userSessionKey);

        if (StringUtils.hasText(oldSessionId)) {
            stringRedisTemplate.delete(
                    SessionRedisKeys.session(oldSessionId)
            );
        }
        stringRedisTemplate.delete(userSessionKey);

        LambdaUpdateWrapper<LoginSessionEntity> wrapper = new LambdaUpdateWrapper<>();
        wrapper.eq(LoginSessionEntity::getUserId, userId)
                .eq(LoginSessionEntity::getStatus, STATUS_ACTIVE)
                .set(LoginSessionEntity::getStatus, STATUS_REVOKED)
                .set(LoginSessionEntity::getRevokeTime, new Date());
        update(wrapper);
    }

    @Override
    // 校验登录会话是否仍有效
    public void assertSessionActive(String sessionId) {
        if (!StringUtils.hasText(sessionId)) {
            throw new AuthenticationException("登录会话无效");
        }
        String userId = stringRedisTemplate.opsForValue().get(
                SessionRedisKeys.session(sessionId)
        );
        if (!StringUtils.hasText(userId)) {
            throw new AuthenticationException(
                    "登录会话已失效，请重新登录"
            );
        }
    }

    @Override
    // 分页查询登录会话列表
    public PageResultVO<LoginSessionVO> listSessions(LoginSessionQueryDTO dto, String currentSessionId) {
        List<LoginSessionEntity> records = list(buildQueryWrapper(dto));
        if (records.isEmpty()) {
            return new PageResultVO<>(0, Collections.emptyList());
        }

        // Redis 是在线状态的实时依据；批量校准，避免逐条访问 Redis。
        applyOnlineStatusFromRedis(records);

        Map<Long, List<LoginSessionEntity>> grouped = records.stream()
                .collect(Collectors.groupingBy(LoginSessionEntity::getUserId));

        List<LoginSessionEntity> representatives = grouped.values().stream()
                .map(this::pickRepresentativeSession)
                .sorted(Comparator
                        .comparing(LoginSessionEntity::getStatus)
                        .thenComparing(LoginSessionEntity::getLoginTime, Comparator.nullsLast(Comparator.reverseOrder())))
                .collect(Collectors.toList());

        int pageNum = dto.getPageNum() != null ? dto.getPageNum() : 1;
        int pageSize = dto.getPageSize() != null ? dto.getPageSize() : 10;
        int fromIndex = Math.max(0, (pageNum - 1) * pageSize);
        int toIndex = Math.min(representatives.size(), fromIndex + pageSize);
        List<LoginSessionEntity> pageRecords = fromIndex >= representatives.size()
                ? Collections.emptyList()
                : representatives.subList(fromIndex, toIndex);

        Map<Long, String> userNameMap = loadUserNameMap(representatives);
        List<LoginSessionVO> rows = toVoList(pageRecords, userNameMap, currentSessionId);
        return new PageResultVO<>((long) representatives.size(), rows);
    }

    @Override
    // 查询指定用户的会话历史
    public List<LoginSessionVO> listSessionHistory(Long userId, String currentSessionId) {
        LoginSessionQueryDTO dto = new LoginSessionQueryDTO();
        dto.setUserId(userId);
        List<LoginSessionEntity> records = list(buildQueryWrapper(dto));
        Map<Long, String> userNameMap = loadUserNameMap(records);
        return toVoList(records, userNameMap, currentSessionId);
    }

    @Override
    // 踢出指定登录设备
    public void kickSession(String sessionId, Long operatorUserId, boolean canManageAll) {
        LoginSessionEntity entity = loginSessionMapper.selectById(sessionId);
        if (entity == null) {
            throw new BusinessException(Module.ModuleType.AUTH, "登录设备不存在", null);
        }
        if (!canManageAll && !operatorUserId.equals(entity.getUserId())) {
            throw new BusinessException(Module.ModuleType.AUTH, "无权踢出该登录设备", null);
        }
        if (STATUS_REVOKED.equals(entity.getStatus())) {
            return;
        }
        revokeSession(sessionId);
    }

    // 构建会话查询条件
    private LambdaQueryWrapper<LoginSessionEntity> buildQueryWrapper(LoginSessionQueryDTO dto) {
        LambdaQueryWrapper<LoginSessionEntity> wrapper = new LambdaQueryWrapper<>();
        if (dto.getUserId() != null) {
            wrapper.eq(LoginSessionEntity::getUserId, dto.getUserId());
        }
        if (StringUtils.hasText(dto.getUserName())) {
            List<Long> userIds = sysUserService.list(new LambdaQueryWrapper<SysUserEntity>()
                            .like(SysUserEntity::getUserName, dto.getUserName()))
                    .stream()
                    .map(SysUserEntity::getUserId)
                    .collect(Collectors.toList());
            if (userIds.isEmpty()) {
                wrapper.eq(LoginSessionEntity::getUserId, -1L);
            } else {
                wrapper.in(LoginSessionEntity::getUserId, userIds);
            }
        }
        wrapper.orderByDesc(LoginSessionEntity::getLoginTime);
        return wrapper;
    }

    // 选取用户的代表性会话
    private LoginSessionEntity pickRepresentativeSession(List<LoginSessionEntity> sessions) {
        return sessions.stream()
                .filter(session -> STATUS_ACTIVE.equals(session.getStatus()))
                .max(Comparator.comparing(LoginSessionEntity::getLoginTime, Comparator.nullsLast(Comparator.naturalOrder())))
                .orElseGet(() -> sessions.stream()
                        .max(Comparator.comparing(LoginSessionEntity::getLoginTime, Comparator.nullsLast(Comparator.naturalOrder())))
                        .orElse(sessions.get(0)));
    }

    /**
     * 将数据库中标记在线的会话与 Redis 实时状态对齐。
     * 这里只修改本次查询结果，不更新历史表；Redis key 不存在即按离线返回。
     */
    // 根据Redis校准会话在线状态
    private void applyOnlineStatusFromRedis(List<LoginSessionEntity> records) {
        List<LoginSessionEntity> activeSessions = records.stream()
                .filter(session -> STATUS_ACTIVE.equals(session.getStatus()))
                .collect(Collectors.toList());
        if (activeSessions.isEmpty()) {
            return;
        }

        List<String> redisKeys = activeSessions.stream()
                .map(LoginSessionEntity::getSessionId)
                .map(SessionRedisKeys::session)
                .collect(Collectors.toList());
        List<String> cachedUserIds = stringRedisTemplate.opsForValue().multiGet(redisKeys);

        for (int i = 0; i < activeSessions.size(); i++) {
            String cachedUserId = cachedUserIds != null && i < cachedUserIds.size()
                    ? cachedUserIds.get(i)
                    : null;
            LoginSessionEntity session = activeSessions.get(i);
            if (!StringUtils.hasText(cachedUserId)
                    || !String.valueOf(session.getUserId()).equals(cachedUserId)) {
                session.setStatus(STATUS_REVOKED);
            }
        }
    }

    // 批量转换会话实体为VO列表
    private List<LoginSessionVO> toVoList(List<LoginSessionEntity> records, Map<Long, String> userNameMap,
                                          String currentSessionId) {
        List<LoginSessionVO> rows = new ArrayList<>(records.size());
        for (LoginSessionEntity record : records) {
            rows.add(toVo(record, userNameMap, currentSessionId));
        }
        return rows;
    }

    // 批量加载用户ID到用户名的映射
    private Map<Long, String> loadUserNameMap(List<LoginSessionEntity> records) {
        List<Long> userIds = records.stream()
                .map(LoginSessionEntity::getUserId)
                .distinct()
                .collect(Collectors.toList());
        if (userIds.isEmpty()) {
            return Collections.emptyMap();
        }
        return sysUserService.listByIds(userIds).stream()
                .collect(Collectors.toMap(SysUserEntity::getUserId, SysUserEntity::getUserName, (a, b) -> a));
    }

    // 转换单条会话实体为VO
    private LoginSessionVO toVo(LoginSessionEntity entity, Map<Long, String> userNameMap, String currentSessionId) {
        LoginSessionVO vo = new LoginSessionVO();
        vo.setSessionId(entity.getSessionId());
        vo.setUserId(entity.getUserId());
        vo.setUserName(userNameMap.get(entity.getUserId()));
        vo.setDeviceName(entity.getDeviceName());
        vo.setLoginIp(entity.getLoginIp());
        vo.setLoginTime(entity.getLoginTime());
        vo.setStatus(entity.getStatus());
        vo.setLoginType(entity.getLoginType());
        vo.setCurrent(StringUtils.hasText(currentSessionId)
                && currentSessionId.equals(entity.getSessionId()));
        return vo;
    }

    // 缓存活跃会话到Redis
    private void cacheActiveSession(String sessionId, Long userId) {
        if (!StringUtils.hasText(sessionId) || userId == null) {
            return;
        }

        stringRedisTemplate.opsForValue().set(
                SessionRedisKeys.session(sessionId),
                String.valueOf(userId),
                jwtExpireSeconds,
                TimeUnit.SECONDS
        );

        stringRedisTemplate.opsForValue().set(
                SessionRedisKeys.userSession(userId),
                sessionId,
                jwtExpireSeconds,
                TimeUnit.SECONDS
        );
    }

    // 截断字符串至指定长度
    private String truncate(String value, int maxLen) {
        if (value.length() <= maxLen) {
            return value;
        }
        return value.substring(0, maxLen);
    }
}
