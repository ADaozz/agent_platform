package org.example.backend.auth.session.service;

import org.example.backend.auth.session.dto.LoginSessionQueryDTO;
import org.example.backend.auth.session.vo.LoginSessionVO;
import org.example.backend.common.vo.PageResultVO;

import java.util.List;

public interface LoginSessionService {

    String createSession(Long userId, String loginIp, String userAgent, String loginType);

    /** 单点登录：吊销该用户全部 active 会话后创建新会话 */
    String createSingleLoginSession(Long userId, String loginIp, String userAgent, String loginType);

    void revokeSession(String sessionId);

    void revokeAllActiveSessions(Long userId);

    void assertSessionActive(String sessionId);

    PageResultVO<LoginSessionVO> listSessions(LoginSessionQueryDTO dto, String currentSessionId);

    List<LoginSessionVO> listSessionHistory(Long userId, String currentSessionId);

    void kickSession(String sessionId, Long operatorUserId, boolean canManageAll);
}
