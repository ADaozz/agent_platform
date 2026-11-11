package org.example.backend.api.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.apache.shiro.authc.AuthenticationException;
import org.example.backend.api.constant.ApiTokenAssets;
import org.example.backend.api.constant.ApiTokenGrantCatalog;
import org.example.backend.api.constant.ApiTokenRedisKeys;
import org.example.backend.api.dto.ApiTokenCreateDTO;
import org.example.backend.api.dto.ApiTokenQueryDTO;
import org.example.backend.api.entity.ApiTokenEntity;
import org.example.backend.api.mapper.ApiTokenMapper;
import org.example.backend.api.service.ApiTokenService;
import org.example.backend.api.vo.ApiTokenGrantGroupVO;
import org.example.backend.api.vo.ApiTokenGrantOptionVO;
import org.example.backend.api.vo.ApiTokenVO;
import org.example.backend.common.exception.BusinessException;
import org.example.backend.common.exception.Module;
import org.example.backend.common.utils.ApiJwtUtils;
import org.example.backend.common.vo.PageResultVO;
import org.example.backend.security.context.LoginUserUtils;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;
import org.springframework.util.StringUtils;

@Service
public class ApiTokenServiceImpl extends ServiceImpl<ApiTokenMapper, ApiTokenEntity> implements ApiTokenService {

    @Resource
    private ApiTokenMapper apiTokenMapper;

    @Resource
    private ApiJwtUtils apiJwtUtils;

    @Resource
    private StringRedisTemplate stringRedisTemplate;

    private static final String STATUS_ACTIVE = "0";
    private static final String STATUS_REVOKED = "1";

    @Override
    // 分页查询当前用户的API Token列表
    public PageResultVO<ApiTokenVO> listApiToken(ApiTokenQueryDTO dto) {
        Long currentUserId = LoginUserUtils.getUserId();
        if (currentUserId == null) {
            throw new BusinessException(Module.ModuleType.AUTH, "未登录", null);
        }
        LambdaQueryWrapper<ApiTokenEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(ApiTokenEntity::getUserId, currentUserId)
                .like(StringUtils.hasText(dto.getTokenName()),
                        ApiTokenEntity::getTokenName, dto.getTokenName())
                .eq(StringUtils.hasText(dto.getAccessKey()),
                        ApiTokenEntity::getAccessKey, dto.getAccessKey())
                .orderByDesc(ApiTokenEntity::getCreateTime);
        int pageNum = dto.getPageNum() != null ? dto.getPageNum() : 1;
        int pageSize = dto.getPageSize() != null ? dto.getPageSize() : 10;
        Page<ApiTokenEntity> page = apiTokenMapper.selectPage(
                new Page<>(pageNum, pageSize),
                wrapper
        );
        List<ApiTokenVO> rows = page.getRecords().stream()
                .map(this::toApiTokenVO)
                .collect(Collectors.toList());
        return new PageResultVO<>(page.getTotal(), rows);
    }

    @Override
    // 查询指定用户的全部API Token
    public PageResultVO<ApiTokenVO> getApiToken(Long userId) {
        LambdaQueryWrapper<ApiTokenEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(ApiTokenEntity::getUserId, userId)
                .orderByDesc(ApiTokenEntity::getCreateTime);
        List<ApiTokenEntity> list = apiTokenMapper.selectList(wrapper);
        List<ApiTokenVO> rows = list.stream()
                .map(this::toApiTokenVO)
                .collect(Collectors.toList());
        return new PageResultVO<>(rows.size(), rows);
    }

    @Override
    // 创建API Token并返回密钥
    public ApiTokenVO createApiToken(ApiTokenCreateDTO dto) {
        Long userId = LoginUserUtils.getUserId();
        if (userId == null) {
            throw new BusinessException(Module.ModuleType.AUTH, "未登录", null);
        }
        ApiTokenAssets.validateAssets(dto.getAsset());
        LambdaQueryWrapper<ApiTokenEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(ApiTokenEntity::getUserId, userId)
                .eq(ApiTokenEntity::getStatus, STATUS_ACTIVE);
        if (count(wrapper) >= 3) {
            throw new BusinessException(Module.ModuleType.API, "不能创建超过三个 API Token", null);
        }
        ApiTokenEntity api = new ApiTokenEntity();
        String accessKey = apiJwtUtils.generateAccessKey();
        Date expireTime = apiJwtUtils.defaultExpireTime();
        String secretKey = apiJwtUtils.createSecretKey(
                accessKey, userId, dto.getAsset(), expireTime);
        api.setAccessKey(accessKey);
        api.setUserId(userId);
        api.setTokenName(dto.getTokenName());
        api.setDetail(dto.getDetail());
        api.setAsset(dto.getAsset());
        api.setSecretKey(secretKey);
        api.setStatus(STATUS_ACTIVE);
        api.setExpireTime(expireTime);
        api.setCreateTime(new Date());
        api.setUpdateTime(new Date());
        save(api);
        cacheApiToken(api);

        ApiTokenVO vo = toApiTokenVO(api);
        vo.setSecretKey(secretKey);
        return vo;
    }

    @Override
    // 吊销指定API Token
    public void deleteApiToken(String tokenId) {
        Long userId = LoginUserUtils.getUserId();
        if (userId == null) {
            throw new BusinessException(Module.ModuleType.AUTH, "未登录", null);
        }
        ApiTokenEntity entity = apiTokenMapper.selectById(tokenId);
        if (entity == null || !userId.equals(entity.getUserId())) {
            throw new BusinessException(Module.ModuleType.API, "API Token 不存在", null);
        }
        entity.setStatus(STATUS_REVOKED);
        entity.setUpdateTime(new Date());
        apiTokenMapper.updateById(entity);
        stringRedisTemplate.delete(ApiTokenRedisKeys.token(entity.getAccessKey()));
    }

    @Override
    // 吊销用户全部活跃API Token
    public void revokeAllByUserId(Long userId) {
        if (userId == null) {
            return;
        }
        List<ApiTokenEntity> activeTokens = apiTokenMapper.selectList(
                new LambdaQueryWrapper<ApiTokenEntity>()
                        .select(ApiTokenEntity::getAccessKey)
                        .eq(ApiTokenEntity::getUserId, userId)
                        .eq(ApiTokenEntity::getStatus, STATUS_ACTIVE)
        );
        LambdaUpdateWrapper<ApiTokenEntity> wrapper = new LambdaUpdateWrapper<>();
        wrapper.eq(ApiTokenEntity::getUserId, userId)
                .eq(ApiTokenEntity::getStatus, STATUS_ACTIVE)
                .set(ApiTokenEntity::getStatus, STATUS_REVOKED)
                .set(ApiTokenEntity::getUpdateTime, new Date());
        update(wrapper);

        if (!activeTokens.isEmpty()) {
            List<String> redisKeys = activeTokens.stream()
                    .map(ApiTokenEntity::getAccessKey)
                    .map(ApiTokenRedisKeys::token)
                    .collect(Collectors.toList());
            stringRedisTemplate.delete(redisKeys);
        }
    }

    @Override
    // 校验API Token是否有效且未吊销
    public void assertTokenActive(String accessKey, String secretKey, Long claimedUserId) {
        if (!StringUtils.hasText(accessKey)
                || !StringUtils.hasText(secretKey)
                || claimedUserId == null) {
            throw new AuthenticationException("API Token 无效");
        }

        String cached = stringRedisTemplate.opsForValue()
                .get(ApiTokenRedisKeys.token(accessKey));
        if (StringUtils.hasText(cached)) {
            assertCachedToken(cached, secretKey, claimedUserId);
            return;
        }

        ApiTokenEntity entity = apiTokenMapper.selectById(accessKey);
        assertDatabaseToken(entity, secretKey, claimedUserId);
        cacheApiToken(entity);
    }

    @Override
    // 物理删除已吊销的API Token记录
    public int purgeRevokedTokens() {
        LambdaQueryWrapper<ApiTokenEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(ApiTokenEntity::getStatus, STATUS_REVOKED);
        long count = count(wrapper);
        if (count == 0) {
            return 0;
        }
        remove(wrapper);
        return (int) count;
    }

    @Override
    // 列出API Token可授权的资源分组选项
    public List<ApiTokenGrantGroupVO> listGrantOptions() {
        List<ApiTokenGrantGroupVO> groups = new ArrayList<>();
        for (Map.Entry<String, List<ApiTokenGrantCatalog.Entry>> entry
                : ApiTokenGrantCatalog.groupedEntries().entrySet()) {
            List<ApiTokenGrantCatalog.Entry> entries = entry.getValue();
            if (entries.isEmpty()) {
                continue;
            }
            ApiTokenGrantGroupVO group = new ApiTokenGrantGroupVO();
            group.setKey(entry.getKey());
            group.setName(entries.get(0).getGroupName());
            List<ApiTokenGrantOptionVO> options = new ArrayList<>();
            for (ApiTokenGrantCatalog.Entry item : entries) {
                ApiTokenGrantOptionVO option = new ApiTokenGrantOptionVO();
                option.setValue(item.getGrantValue());
                option.setLabel(item.getLabel());
                options.add(option);
            }
            group.setOptions(options);
            groups.add(group);
        }
        return groups;
    }

    // 将有效Token缓存到Redis
    private void cacheApiToken(ApiTokenEntity entity) {
        if (entity == null
                || !StringUtils.hasText(entity.getAccessKey())
                || !StringUtils.hasText(entity.getSecretKey())
                || entity.getUserId() == null
                || !STATUS_ACTIVE.equals(entity.getStatus())) {
            return;
        }
        long ttlSeconds = calculateTtlSeconds(entity.getExpireTime());
        if (ttlSeconds <= 0) {
            return;
        }
        String value = entity.getUserId() + ":" + sha256(entity.getSecretKey());
        stringRedisTemplate.opsForValue().set(
                ApiTokenRedisKeys.token(entity.getAccessKey()),
                value,
                ttlSeconds,
                TimeUnit.SECONDS
        );
    }

    // 校验Redis缓存中的Token
    private void assertCachedToken(String cached, String secretKey, Long claimedUserId) {
        int separator = cached.indexOf(':');
        if (separator <= 0 || separator == cached.length() - 1) {
            throw new AuthenticationException("API Token 缓存数据无效");
        }
        String cachedUserId = cached.substring(0, separator);
        String cachedSecretHash = cached.substring(separator + 1);
        if (!String.valueOf(claimedUserId).equals(cachedUserId)
                || !constantTimeEquals(cachedSecretHash, sha256(secretKey))) {
            throw new AuthenticationException("API Token 无效、已吊销或已过期");
        }
    }

    // 校验数据库中的Token
    private void assertDatabaseToken(ApiTokenEntity entity, String secretKey, Long claimedUserId) {
        if (entity == null
                || !claimedUserId.equals(entity.getUserId())
                || !STATUS_ACTIVE.equals(entity.getStatus())
                || !constantTimeEquals(sha256(secretKey), sha256(entity.getSecretKey()))
                || isExpired(entity.getExpireTime())) {
            throw new AuthenticationException("API Token 无效、已吊销或已过期");
        }
    }

    // 判断Token是否已过期
    private boolean isExpired(Date expireTime) {
        return expireTime != null && expireTime.before(new Date());
    }

    // 计算Token剩余有效秒数
    private long calculateTtlSeconds(Date expireTime) {
        if (expireTime == null) {
            return TimeUnit.DAYS.toSeconds(1);
        }
        long remainingMillis = expireTime.getTime() - System.currentTimeMillis();
        return remainingMillis <= 0 ? 0 : Math.max(1, (remainingMillis + 999) / 1000);
    }

    // 计算字符串的SHA-256哈希
    private String sha256(String value) {
        if (value == null) {
            return "";
        }
        try {
            byte[] bytes = MessageDigest.getInstance("SHA-256")
                    .digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder result = new StringBuilder(bytes.length * 2);
            for (byte item : bytes) {
                result.append(String.format("%02x", item & 0xff));
            }
            return result.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("当前运行环境不支持 SHA-256", e);
        }
    }

    // 常量时间比较两个字符串
    private boolean constantTimeEquals(String left, String right) {
        if (left == null || right == null) {
            return false;
        }
        return MessageDigest.isEqual(
                left.getBytes(StandardCharsets.UTF_8),
                right.getBytes(StandardCharsets.UTF_8)
        );
    }

    // 将Token实体转换为VO
    private ApiTokenVO toApiTokenVO(ApiTokenEntity entity) {
        ApiTokenVO vo = new ApiTokenVO();
        vo.setUserId(entity.getUserId());
        vo.setAccessKey(entity.getAccessKey());
        vo.setTokenName(entity.getTokenName());
        vo.setDetail(entity.getDetail());
        vo.setAsset(entity.getAsset());
        vo.setStatus(entity.getStatus());
        vo.setExpireTime(entity.getExpireTime());
        vo.setCreateTime(entity.getCreateTime());
        return vo;
    }
}
