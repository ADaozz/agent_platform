package org.example.backend.system.permission.controller;

import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.example.backend.common.annotation.Log;
import org.example.backend.common.enums.BusinessType;
import org.example.backend.common.result.AjaxResult;
import org.example.backend.system.permission.dto.SysPermissionQueryDTO;
import org.example.backend.system.permission.service.SysPermissionService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/system/permission")
public class SysPermissionController {

    @Autowired
    private SysPermissionService sysPermissionService;

    @Log(title = "权限管理", businessType = BusinessType.QUERY)
    @GetMapping
    @RequiresPermissions("system:role:list")
    public AjaxResult list(SysPermissionQueryDTO query) {
        return AjaxResult.success("成功", sysPermissionService.listPermissionInfo(query));
    }

    @Log(title = "权限管理", businessType = BusinessType.QUERY, isSaveResponseData = false)
    @GetMapping("/options")
    @RequiresPermissions("system:role:list")
    public AjaxResult permissionOptions() {
        return AjaxResult.success("成功", sysPermissionService.listAllPermissionOptions());
    }
}
