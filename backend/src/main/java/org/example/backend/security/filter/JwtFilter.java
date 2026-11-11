package org.example.backend.security.filter;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.shiro.authc.AuthenticationException;
import org.apache.shiro.authc.AuthenticationToken;
import org.apache.shiro.subject.Subject;
import org.apache.shiro.util.StringUtils;
import org.apache.shiro.web.filter.authc.AuthenticatingFilter;
import org.example.backend.agent.AgentRuntimeCookie;
import org.example.backend.api.constant.ApiTokenAssets;
import org.example.backend.common.result.AjaxResult;
import org.example.backend.security.token.JwtToken;
import org.example.backend.security.token.ApiAuthToken;

import javax.servlet.ServletRequest;
import javax.servlet.ServletResponse;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.List;
import javax.annotation.Resource;


public class JwtFilter extends AuthenticatingFilter {

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    @Resource
    private org.example.backend.common.utils.ApiJwtUtils apiJwtUtils;

    @Override
    protected boolean isAccessAllowed(ServletRequest request, ServletResponse response, Object mappedValue) {
        HttpServletRequest httpRequest = (HttpServletRequest) request;
        if ("/login".equals(httpRequest.getServletPath())
                || "/login/cert".equals(httpRequest.getServletPath())
                || "/login/cert/check".equals(httpRequest.getServletPath())
                || "/login/cert/debug".equals(httpRequest.getServletPath())) {
            return true;
        }
        if (hasApiHeaders(httpRequest)) {
            return false;
        }
        Subject subject = getSubject(request, response);
        return subject != null && subject.isAuthenticated();
    }

    // 从请求中解析JWT
    @Override
    protected AuthenticationToken createToken(ServletRequest request, ServletResponse response) throws Exception{
        HttpServletRequest httpRequest = (HttpServletRequest) request;
        String accessKey = httpRequest.getHeader("X-Access-Key");
        String secretKey = httpRequest.getHeader("X-Secret-Key");
        if (StringUtils.hasText(accessKey) || StringUtils.hasText(secretKey)) {
            if (!StringUtils.hasText(accessKey) || !StringUtils.hasText(secretKey)) {
                return null;
            }
            return new ApiAuthToken(accessKey.trim(), secretKey.trim());
        }
        final String BEARER_PREFIX = "Bearer ";
        String authorization = httpRequest.getHeader("Authorization");
        if (!StringUtils.hasText(authorization)) {
            String cookieToken = AgentRuntimeCookie.read(httpRequest);
            return cookieToken == null ? null : new JwtToken(cookieToken);
        }
        authorization = authorization.trim();
        if (authorization.regionMatches(true, 0, BEARER_PREFIX, 0, BEARER_PREFIX.length())) {
            authorization = authorization.substring(BEARER_PREFIX.length()).trim();
        } else {
            return null; // 或者按你的策略：允许裸 token
        }
        if (!StringUtils.hasText(authorization)) {
            return null;
        }
        return new JwtToken(authorization);
    }

    // shrio接口拦截规则
    @Override
    protected boolean onAccessDenied(ServletRequest request, ServletResponse response) throws Exception{

        if ("OPTIONS".equalsIgnoreCase(((HttpServletRequest) request).getMethod())) {
            return true;
        }
        HttpServletRequest httpRequest = (HttpServletRequest) request;
        if (hasApiHeaders(httpRequest)) {
            String requiredGrant = ApiTokenAssets.requiredGrant(
                    httpRequest.getMethod(), httpRequest.getServletPath());
            if (requiredGrant == null) {
                writeForbidden(response, "API Token 未授权访问该路径");
                return false;
            }
            if (!hasAssetPermission(httpRequest, requiredGrant)) {
                writeForbidden(response, "API Token 未授权访问该业务资源");
                return false;
            }
        }
        if (createToken(request, response) == null) {
            writeUnauthorized(response, "未登录或 token 缺失");
            return false;
        }
        // 有 token：交给 Shiro → UserRealm 验 JWT（这就是「免登录」）
        return executeLogin(request, response);
    }

    private boolean hasApiHeaders(HttpServletRequest request) {
        return StringUtils.hasText(request.getHeader("X-Access-Key"))
                || StringUtils.hasText(request.getHeader("X-Secret-Key"));
    }

    private boolean hasAssetPermission(HttpServletRequest request, String requiredGrant) {
        try {
            String secretKey = request.getHeader("X-Secret-Key");
            String accessKey = request.getHeader("X-Access-Key");
            io.jsonwebtoken.Claims claims = apiJwtUtils.parseToken(secretKey);
            if (!apiJwtUtils.isApiToken(claims)
                    || !accessKey.equals(apiJwtUtils.getAccessKey(claims))) {
                return false;
            }
            List<String> assets = apiJwtUtils.getAssets(claims);
            return ApiTokenAssets.isGranted(assets, requiredGrant);
        } catch (Exception e) {
            return false;
        }
    }

    @Override
    protected boolean onLoginFailure(AuthenticationToken token, AuthenticationException e,
                                     ServletRequest request, ServletResponse response) {
        try {
            writeUnauthorized(response, "token 无效或已过期");
        } catch (IOException ex) {
            throw new RuntimeException(ex);
        }
        return false;
    }

    private void writeUnauthorized(ServletResponse response, String message) throws IOException {
        HttpServletResponse httpResponse = (HttpServletResponse) response;
        httpResponse.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        httpResponse.setCharacterEncoding("UTF-8");
        httpResponse.setContentType("application/json;charset=UTF-8");
        httpResponse.getWriter().write(
                OBJECT_MAPPER.writeValueAsString(AjaxResult.error(message, null))
        );
    }

    private void writeForbidden(ServletResponse response, String message) throws IOException {
        HttpServletResponse httpResponse = (HttpServletResponse) response;
        httpResponse.setStatus(HttpServletResponse.SC_FORBIDDEN);
        httpResponse.setCharacterEncoding("UTF-8");
        httpResponse.setContentType("application/json;charset=UTF-8");
        httpResponse.getWriter().write(
                OBJECT_MAPPER.writeValueAsString(AjaxResult.error(message, null))
        );
    }
}
