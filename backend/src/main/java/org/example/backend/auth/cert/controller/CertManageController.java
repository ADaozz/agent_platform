package org.example.backend.auth.cert.controller;

import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.example.backend.auth.cert.dto.CertApplyQueryDTO;
import org.example.backend.auth.cert.dto.CertApproveDTO;
import org.example.backend.auth.cert.dto.CertRejectDTO;
import org.example.backend.auth.cert.dto.UserCertQueryDTO;
import org.example.backend.auth.cert.service.CertApplyService;
import org.example.backend.common.annotation.Log;
import org.example.backend.common.enums.BusinessType;
import org.example.backend.common.result.AjaxResult;
import org.example.backend.security.context.LoginUserUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.validation.Valid;

@RestController
@Validated
@RequestMapping("/system/cert")
public class CertManageController {

    @Autowired
    private CertApplyService certApplyService;

    @Log(title = "证书管理", businessType = BusinessType.QUERY)
    @GetMapping("/apply")
    @RequiresPermissions("system:cert:list")
    public AjaxResult listApplies(CertApplyQueryDTO query) {
        return AjaxResult.success("成功", certApplyService.listApplies(query));
    }

    @Log(title = "证书管理", businessType = BusinessType.QUERY)
    @GetMapping
    @RequiresPermissions("system:cert:list")
    public AjaxResult listCerts(UserCertQueryDTO query) {
        return AjaxResult.success("成功", certApplyService.listCerts(query));
    }

    @Log(title = "证书管理", businessType = BusinessType.QUERY)
    @GetMapping("/{certId}")
    @RequiresPermissions("system:cert:list")
    public AjaxResult detail(@PathVariable Long certId) {
        return AjaxResult.success("成功", certApplyService.getCertDetail(certId));
    }

    @Log(title = "证书管理", businessType = BusinessType.UPDATE)
    @PostMapping("/apply/{applyId}/approve")
    @RequiresPermissions("system:cert:approve")
    public AjaxResult approve(@PathVariable Long applyId, @Valid @RequestBody CertApproveDTO dto) {
        return AjaxResult.success("审批通过",
                certApplyService.approve(applyId, LoginUserUtils.getUserId(), dto));
    }

    @Log(title = "证书管理", businessType = BusinessType.UPDATE)
    @PostMapping("/apply/{applyId}/reject")
    @RequiresPermissions("system:cert:approve")
    public AjaxResult reject(@PathVariable Long applyId, @RequestBody(required = false) CertRejectDTO dto) {
        certApplyService.reject(applyId, LoginUserUtils.getUserId(), dto);
        return AjaxResult.success("已拒绝申请", null);
    }

    @Log(title = "证书管理", businessType = BusinessType.UPDATE)
    @PutMapping("/{certId}/revoke")
    @RequiresPermissions("system:cert:revoke")
    public AjaxResult revoke(@PathVariable Long certId) {
        certApplyService.revokeCert(certId, LoginUserUtils.getUserId());
        return AjaxResult.success("证书已吊销", null);
    }
}
