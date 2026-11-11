package org.example.backend.system.user.controller;

import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.example.backend.common.annotation.Log;
import org.example.backend.common.enums.BusinessType;
import org.example.backend.common.result.AjaxResult;
import org.example.backend.system.user.dto.SysUserCreateDTO;
import org.example.backend.system.user.dto.SysUserQueryDTO;
import org.example.backend.system.user.dto.SysUserRoleAssignDTO;
import org.example.backend.system.user.dto.SysUserUpdateDTO;
import org.example.backend.system.user.service.SysUserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;

@RestController
@Validated
@RequestMapping("/system/user")
public class SysUserController {

    @Autowired
    private SysUserService sysUserService;

    @Log(title = "用户管理", businessType = BusinessType.QUERY)
    @GetMapping
    @RequiresPermissions("system:user:list")
    public AjaxResult list(SysUserQueryDTO query) {
        return AjaxResult.success("获取用户信息成功", sysUserService.listUserInfo(query));
    }

    @Log(title = "用户管理", businessType = BusinessType.INSERT, excludeParamNames = {"passWord"})
    @PostMapping
    @RequiresPermissions("system:user:add")
    public AjaxResult add(@Valid @RequestBody SysUserCreateDTO dto) {
        sysUserService.createUser(dto);
        return AjaxResult.success("新增成功", null);
    }

    @Log(title = "用户管理", businessType = BusinessType.UPDATE, excludeParamNames = {"passWord"})
    @PutMapping
    @RequiresPermissions("system:user:edit")
    public AjaxResult update(@Valid @RequestBody SysUserUpdateDTO dto) {
        sysUserService.updateUser(dto);
        return AjaxResult.success("更新成功", null);
    }

    @Log(title = "用户管理", businessType = BusinessType.GRANT)
    @PutMapping("/authRole")
    @RequiresPermissions("system:user:edit")
    public AjaxResult authRole(@Valid @RequestBody SysUserRoleAssignDTO dto) {
        sysUserService.assignUserRoles(dto);
        return AjaxResult.success("分配角色成功", null);
    }

    @Log(title = "用户管理", businessType = BusinessType.DELETE)
    @DeleteMapping("/{userId}")
    @RequiresPermissions("system:user:delete")
    public AjaxResult delete(@PathVariable Long userId) {
        sysUserService.deleteUser(userId);
        return AjaxResult.success("删除成功", null);
    }
}
