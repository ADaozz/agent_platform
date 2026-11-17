package org.example.backend.security.filter;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.shiro.authc.AuthenticationException;
import org.apache.shiro.authc.AuthenticationToken;
import org.apache.shiro.subject.Subject;
import org.apache.shiro.util.StringUtils;
import org.apache.shiro.web.filter.authc.AuthenticatingFilter;
import org.example.backend.agent.AgentRuntimeCookie;
import org.example.backend.common.result.AjaxResult;
import org.example.backend.security.token.JwtToken;

import javax.servlet.ServletRequest;
import javax.servlet.ServletResponse;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.IOException;

public class JwtFilter extends AuthenticatingFilter {

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    @Override
    protected boolean isAccessAllowed(ServletRequest request, ServletResponse response, Object mappedValue) {
        HttpServletRequest httpRequest = (HttpServletRequest) request;
        if ("/login".equals(httpRequest.getServletPath())
                || "/register".equals(httpRequest.getServletPath())
                || "/register/code".equals(httpRequest.getServletPath())
                || "/login/cert".equals(httpRequest.getServletPath())
                || "/login/cert/availability".equals(httpRequest.getServletPath())
                || "/login/cert/check".equals(httpRequest.getServletPath())
                || "/login/cert/debug".equals(httpRequest.getServletPath())) {
            return true;
        }
        Subject subject = getSubject(request, response);
        return subject != null && subject.isAuthenticated();
    }

    @Override
    protected AuthenticationToken createToken(ServletRequest request, ServletResponse response) {
        HttpServletRequest httpRequest = (HttpServletRequest) request;
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
            return null;
        }
        if (!StringUtils.hasText(authorization)) {
            return null;
        }
        return new JwtToken(authorization);
    }

    @Override
    protected boolean onAccessDenied(ServletRequest request, ServletResponse response) throws Exception {
        if ("OPTIONS".equalsIgnoreCase(((HttpServletRequest) request).getMethod())) {
            return true;
        }
        if (createToken(request, response) == null) {
            writeUnauthorized(response, "未登录或 token 缺失");
            return false;
        }
        return executeLogin(request, response);
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
}
