package org.example.backend.auth.cert.controller;

import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.example.backend.auth.cert.dto.CertApplyCreateDTO;
import org.example.backend.auth.cert.service.CertApplyService;
import org.example.backend.common.annotation.Log;
import org.example.backend.common.enums.BusinessType;
import org.example.backend.common.result.AjaxResult;
import org.example.backend.security.context.LoginUserUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.io.File;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;

@RestController
@Validated
@RequestMapping("/system/cert/mine")
public class UserCertController {

    @Autowired
    private CertApplyService certApplyService;

    @Log(title = "我的证书", businessType = BusinessType.QUERY)
    @GetMapping
    @RequiresPermissions("system:cert:mine")
    public AjaxResult overview() {
        return AjaxResult.success("成功", certApplyService.getMyOverview(LoginUserUtils.getUserId()));
    }

    @Log(title = "我的证书", businessType = BusinessType.QUERY)
    @GetMapping("/apply")
    @RequiresPermissions("system:cert:mine")
    public AjaxResult myApplies() {
        return AjaxResult.success("成功", certApplyService.listMyApplies(LoginUserUtils.getUserId()));
    }

    @Log(title = "我的证书", businessType = BusinessType.INSERT)
    @PostMapping("/apply")
    @RequiresPermissions("system:cert:mine")
    public AjaxResult apply(@RequestBody(required = false) CertApplyCreateDTO dto) {
        certApplyService.apply(LoginUserUtils.getUserId(), dto != null ? dto : new CertApplyCreateDTO());
        return AjaxResult.success("申请已提交，请等待管理员审批", null);
    }

    @Log(title = "我的证书", businessType = BusinessType.INSERT)
    @PostMapping("/reissue")
    @RequiresPermissions("system:cert:mine")
    public AjaxResult reissue(@RequestBody(required = false) CertApplyCreateDTO dto) {
        certApplyService.reissue(LoginUserUtils.getUserId(), dto != null ? dto : new CertApplyCreateDTO());
        return AjaxResult.success("重发申请已提交，请等待管理员审批", null);
    }

    @Log(title = "我的证书", businessType = BusinessType.EXPORT, isSaveResponseData = false)
    @GetMapping("/download/{applyId}")
    @RequiresPermissions("system:cert:mine")
    public ResponseEntity<FileSystemResource> download(@PathVariable Long applyId) throws Exception {
        File file = certApplyService.downloadBundle(LoginUserUtils.getUserId(), applyId);
        String filename = URLEncoder.encode("client-cert-" + applyId + ".zip", StandardCharsets.UTF_8.name())
                .replace("+", "%20");
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename*=UTF-8''" + filename)
                .contentType(MediaType.APPLICATION_OCTET_STREAM)
                .body(new FileSystemResource(file));
    }

    @Log(title = "我的证书", businessType = BusinessType.QUERY, isSaveResponseData = false)
    @PostMapping("/reveal-password/{applyId}")
    @RequiresPermissions("system:cert:mine")
    public AjaxResult revealPassword(@PathVariable Long applyId) {
        return AjaxResult.success("成功",
                certApplyService.revealP12Password(LoginUserUtils.getUserId(), applyId));
    }
}
