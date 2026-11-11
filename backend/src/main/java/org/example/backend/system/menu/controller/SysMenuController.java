package org.example.backend.system.menu.controller;

import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.example.backend.common.annotation.Log;
import org.example.backend.common.enums.BusinessType;
import org.example.backend.common.result.AjaxResult;
import org.example.backend.system.menu.service.SysMenuService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/system/menu")
public class SysMenuController {

    @Autowired
    private SysMenuService sysMenuService;

    @Log(title = "菜单管理", businessType = BusinessType.QUERY, isSaveResponseData = false)
    @GetMapping("/permTree")
    @RequiresPermissions("system:role:list")
    public AjaxResult permTree(@RequestParam(required = false) Long roleId) {
        return AjaxResult.success("成功", sysMenuService.buildPermTree(roleId));
    }
}
