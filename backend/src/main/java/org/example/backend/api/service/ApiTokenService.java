package org.example.backend.api.service;

import com.baomidou.mybatisplus.extension.service.IService;
import org.example.backend.api.dto.ApiTokenCreateDTO;
import org.example.backend.api.dto.ApiTokenQueryDTO;
import org.example.backend.api.entity.ApiTokenEntity;
import org.example.backend.api.vo.ApiTokenGrantGroupVO;
import org.example.backend.api.vo.ApiTokenGrantOptionVO;
import org.example.backend.api.vo.ApiTokenVO;
import org.example.backend.common.vo.PageResultVO;

import java.util.List;

public interface ApiTokenService extends IService<ApiTokenEntity> {

    PageResultVO<ApiTokenVO> listApiToken(ApiTokenQueryDTO dto);

    PageResultVO<ApiTokenVO> getApiToken(Long userId);

    ApiTokenVO createApiToken(ApiTokenCreateDTO dto);

    void deleteApiToken(String tokenId);

    /** 吊销指定用户下所有有效 API Token */
    void revokeAllByUserId(Long userId);

    /** Redis 优先校验 API Token；缓存未命中时回源数据库并回填。 */
    void assertTokenActive(String accessKey, String secretKey, Long claimedUserId);

    /** 物理删除 status=已吊销 的凭证，返回删除条数 */
    int purgeRevokedTokens();

    /** 新建 Token 时可勾选的开放能力（含当前用户是否可授出） */
    List<ApiTokenGrantGroupVO> listGrantOptions();
}
