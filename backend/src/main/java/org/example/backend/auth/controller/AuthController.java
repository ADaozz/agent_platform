package org.example.backend.auth.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.example.backend.agent.AgentRuntimeCookie;
import org.example.backend.auth.dto.LoginDTO;
import org.example.backend.auth.service.AuthService;
import org.example.backend.auth.vo.LoginVO;
import org.example.backend.common.annotation.Log;
import org.example.backend.common.enums.BusinessType;
import org.example.backend.common.enums.OperatorType;
import org.example.backend.common.exception.BusinessException;
import org.example.backend.common.result.AjaxResult;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.util.StringUtils;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseBody;
import org.springframework.web.bind.annotation.RestController;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import javax.validation.Valid;
import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
@Validated
public class AuthController {

    @Autowired
    private AuthService authService;

    @Autowired
    private ObjectMapper objectMapper;

    /** 证书登录后允许跳回的前端 Origin（如 Vite 开发地址）；登录令牌在 URL 中，禁止放开任意地址 */
    @Value("${cert.login.allowed-origins:}")
    private List<String> allowedOrigins;

    @Log(title = "认证", businessType = BusinessType.OTHER, operatorType = OperatorType.OTHER,
            excludeParamNames = {"passWord"})
    @PostMapping("/login")
    @ResponseBody
    public AjaxResult login(@Valid @RequestBody LoginDTO dto, HttpServletRequest request) {
        return AjaxResult.success("登录成功", authService.login(dto, request));
    }

    @Log(title = "认证", businessType = BusinessType.OTHER, operatorType = OperatorType.OTHER)
    @GetMapping("/login/cert")
    public void loginByCertGet(HttpServletResponse response,
                               @RequestParam(value = "redirect", defaultValue = "1") String redirect,
                               @RequestParam(value = "origin", required = false) String origin)
            throws IOException {
        String action = "/login/cert?redirect=" + ("1".equals(redirect) ? "1" : "0");
        if (isAllowedOrigin(origin)) {
            action += "&origin=" + URLEncoder.encode(origin, StandardCharsets.UTF_8.name());
        }
        response.setContentType("text/html;charset=UTF-8");
        response.getWriter().write(
                "<!DOCTYPE html><html><head><meta charset=\"UTF-8\"><title>证书登录</title></head><body>"
                        + "<p>正在建立 mTLS 连接并提交证书登录…</p>"
                        + "<form id=\"f\" method=\"POST\" action=\"" + action + "\"></form>"
                        + "<script>document.getElementById('f').submit();</script>"
                        + "</body></html>");
    }

    @Log(title = "认证", businessType = BusinessType.OTHER, operatorType = OperatorType.OTHER)
    @PostMapping("/login/cert")
    public Object loginByCert(HttpServletRequest request,
                              HttpServletResponse response,
                              @RequestParam(value = "redirect", required = false) String redirect,
                              @RequestParam(value = "origin", required = false) String origin)
            throws IOException {
        boolean browserRedirect = "1".equals(redirect);
        try {
            LoginVO vo = authService.loginByCert(request);
            if (browserRedirect) {
                redirectCertLoginSuccess(request, response, vo, origin);
                return null;
            }
            return AjaxResult.success("登录成功", vo);
        } catch (BusinessException e) {
            if (browserRedirect) {
                redirectCertLoginError(request, response, e.getMessage(), origin);
                return null;
            }
            throw e;
        }
    }

    private void redirectCertLoginSuccess(HttpServletRequest request, HttpServletResponse response, LoginVO vo,
                                          String origin) throws IOException {
        String payload = Base64.getUrlEncoder().withoutPadding().encodeToString(objectMapper.writeValueAsBytes(vo));
        response.sendRedirect(buildLoginUrl(request, origin) + "#certLogin=" + payload);
    }

    private void redirectCertLoginError(HttpServletRequest request, HttpServletResponse response, String message,
                                        String origin) throws IOException {
        response.sendRedirect(buildLoginUrl(request, origin) + "?certError="
                + URLEncoder.encode(message, StandardCharsets.UTF_8.name()));
    }

    private boolean isAllowedOrigin(String origin) {
        return StringUtils.hasText(origin) && allowedOrigins.contains(origin);
    }

    private String buildLoginUrl(HttpServletRequest request, String origin) {
        if (isAllowedOrigin(origin)) {
            return origin + "/login";
        }
        String host = request.getHeader("Host");
        if (StringUtils.hasText(host) && host.contains(":")) {
            host = host.substring(0, host.indexOf(':'));
        }
        if (!StringUtils.hasText(host)) {
            host = "localhost";
        }
        return "https://" + host + "/login";
    }

    /** 8443 mTLS 诊断（纯文本）：https://host:8443/debug-cert */
    @GetMapping(value = "/login/cert/debug", produces = "text/plain;charset=UTF-8")
    public String certDebugPlain(HttpServletRequest request) {
        String verify = request.getHeader("X-Client-Verify");
        return "verify=" + (StringUtils.hasText(verify) ? verify : "NONE") + "\n"
                + "dn=" + nullToEmpty(request.getHeader("X-Client-DN")) + "\n"
                + "hasCert=" + StringUtils.hasText(request.getHeader("X-Client-Cert")) + "\n";
    }

    private static String nullToEmpty(String value) {
        return value == null ? "" : value;
    }

    /** 8443 mTLS 诊断：浏览器直接访问 https://host:8443/cert-check 查看是否提交了客户端证 */
    @GetMapping("/login/cert/check")
    public AjaxResult certCheck(HttpServletRequest request) {
        Map<String, Object> data = new LinkedHashMap<>();
        String verify = request.getHeader("X-Client-Verify");
        data.put("verify", StringUtils.hasText(verify) ? verify : "NONE");
        data.put("dn", request.getHeader("X-Client-DN"));
        data.put("hasCert", StringUtils.hasText(request.getHeader("X-Client-Cert")));
        data.put("ok", "SUCCESS".equalsIgnoreCase(verify));
        return AjaxResult.success("ok", data);
    }

    @Log(title = "认证", businessType = BusinessType.OTHER, operatorType = OperatorType.OTHER)
    @PostMapping("/logout")
    public AjaxResult logout(HttpServletRequest request, HttpServletResponse response) {
        authService.logout(request);
        response.addHeader(HttpHeaders.SET_COOKIE, AgentRuntimeCookie.clear(AgentRuntimeCookie.isSecure(request)).toString());
        return AjaxResult.success("退出成功", null);
    }

    @Log(title = "认证", businessType = BusinessType.QUERY, isSaveRequestData = false)
    @GetMapping("/user/info")
    public AjaxResult getInfo() {
        return AjaxResult.success("成功", authService.getCurrentUser());
    }
}
