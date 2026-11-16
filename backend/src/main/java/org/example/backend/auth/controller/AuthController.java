package org.example.backend.auth.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.example.backend.agent.AgentRuntimeCookie;
import org.example.backend.auth.cert.util.CertLoginRedirect;
import org.example.backend.auth.cert.util.CertTrustedProxy;
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
import java.util.Map;

@RestController
@Validated
public class AuthController {

    @Autowired
    private AuthService authService;

    @Autowired
    private ObjectMapper objectMapper;

    /** 逗号分隔的精确 HTTPS Origin；登录令牌只回到这里或 public-origin */
    @Value("${cert.login.allowed-origins:}")
    private String allowedOriginsCsv;

    @Value("${cert.login.public-origin:}")
    private String publicOrigin;

    @Value("${cert.login.enabled:false}")
    private boolean certLoginEnabled;

    @Value("${cert.login.trusted-proxies:127.0.0.1,::1}")
    private String trustedProxiesCsv;

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
                redirectCertLoginSuccess(response, vo, origin);
                return null;
            }
            return AjaxResult.success("登录成功", vo);
        } catch (BusinessException e) {
            if (browserRedirect) {
                // 用稳定错误码回跳，登录页可给出可操作提示；勿回传任意异常原文
                redirectCertLoginError(response, certLoginErrorCode(e.getMessage()), origin);
                return null;
            }
            throw e;
        } catch (IllegalStateException e) {
            response.sendError(HttpServletResponse.SC_INTERNAL_SERVER_ERROR, "证书登录回跳地址未配置");
            return null;
        }
    }

    private void redirectCertLoginSuccess(HttpServletResponse response, LoginVO vo, String origin) throws IOException {
        String payload = Base64.getUrlEncoder().withoutPadding().encodeToString(objectMapper.writeValueAsBytes(vo));
        response.sendRedirect(buildLoginUrl(origin) + "#certLogin=" + payload);
    }

    private void redirectCertLoginError(HttpServletResponse response, String message, String origin) throws IOException {
        response.sendRedirect(buildLoginUrl(origin) + "?certError="
                + URLEncoder.encode(message, StandardCharsets.UTF_8.name()));
    }

    /** Map backend refusal text to a small allowlist of URL-safe codes for the login page. */
    static String certLoginErrorCode(String message) {
        if (!StringUtils.hasText(message)) {
            return "cert_login_failed";
        }
        if (message.contains("未检测到") || message.contains("解析失败")) {
            return "no_client_cert";
        }
        if (message.contains("未绑定") || message.contains("未签发")) {
            return "cert_not_bound";
        }
        if (message.contains("过期")) {
            return "cert_expired";
        }
        if (message.contains("未启用") || message.contains("可信代理") || message.contains("代理")) {
            return "cert_proxy";
        }
        if (message.contains("停用")) {
            return "account_disabled";
        }
        return "cert_login_failed";
    }

    private boolean isAllowedOrigin(String origin) {
        return CertLoginRedirect.isAllowedRedirectOrigin(origin, CertLoginRedirect.parseOrigins(allowedOriginsCsv));
    }

    private String buildLoginUrl(String origin) {
        return CertLoginRedirect.loginUrl(origin, publicOrigin, CertLoginRedirect.parseOrigins(allowedOriginsCsv));
    }

    /** 登录页据此决定是否展示证书登录；未启用时不提供不可用入口。 */
    @GetMapping("/login/cert/availability")
    public AjaxResult certAvailability() {
        Map<String, Object> data = new LinkedHashMap<>();
        boolean ready = certLoginEnabled && CertLoginRedirect.isExactHttpsOrigin(publicOrigin)
                && !CertTrustedProxy.parseProxies(trustedProxiesCsv).isEmpty();
        data.put("enabled", ready);
        return AjaxResult.success("ok", data);
    }

    /** 8443 mTLS 诊断（纯文本）：https://host:8443/debug-cert */
    @GetMapping(value = "/login/cert/debug", produces = "text/plain;charset=UTF-8")
    public String certDebugPlain(HttpServletRequest request) {
        String verify = request.getHeader("X-Client-Verify");
        boolean trusted = CertTrustedProxy.isTrusted(
                certLoginEnabled,
                CertTrustedProxy.parseProxies(trustedProxiesCsv),
                request);
        return "verify=" + (StringUtils.hasText(verify) ? verify : "NONE") + "\n"
                + "dn=" + nullToEmpty(request.getHeader("X-Client-DN")) + "\n"
                + "hasCert=" + StringUtils.hasText(request.getHeader("X-Client-Cert")) + "\n"
                + "proxyTrusted=" + trusted + "\n"
                + "certLoginEnabled=" + certLoginEnabled + "\n";
    }

    private static String nullToEmpty(String value) {
        return value == null ? "" : value;
    }

    /** 8443 mTLS 诊断：浏览器直接访问 https://host:8443/cert-check 查看是否提交了客户端证 */
    @GetMapping("/login/cert/check")
    public AjaxResult certCheck(HttpServletRequest request) {
        Map<String, Object> data = new LinkedHashMap<>();
        String verify = request.getHeader("X-Client-Verify");
        boolean trusted = CertTrustedProxy.isTrusted(
                certLoginEnabled,
                CertTrustedProxy.parseProxies(trustedProxiesCsv),
                request);
        data.put("verify", StringUtils.hasText(verify) ? verify : "NONE");
        data.put("dn", request.getHeader("X-Client-DN"));
        data.put("hasCert", StringUtils.hasText(request.getHeader("X-Client-Cert")));
        data.put("proxyTrusted", trusted);
        data.put("certLoginEnabled", certLoginEnabled);
        // ok only when proxy boundary holds and Nginx reported SUCCESS
        data.put("ok", trusted && "SUCCESS".equalsIgnoreCase(verify));
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
