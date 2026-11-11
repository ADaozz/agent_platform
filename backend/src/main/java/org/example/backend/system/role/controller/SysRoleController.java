package org.example.backend.system.role.controller;

import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.example.backend.common.annotation.Log;
import org.example.backend.common.enums.BusinessType;
import org.example.backend.common.result.AjaxResult;
import org.example.backend.system.role.dto.SysRoleCreateDTO;
import org.example.backend.system.role.dto.SysRolePermAssignDTO;
import org.example.backend.system.role.dto.SysRoleQueryDTO;
import org.example.backend.system.role.dto.SysRoleUpdateDTO;
import org.example.backend.system.role.service.SysRoleService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;

@RestController
@Validated
@RequestMapping("/system/role")
public class SysRoleController {

    @Autowired
    private SysRoleService sysRoleService;

    @Log(title = "角色管理", businessType = BusinessType.QUERY)
    @GetMapping
    @RequiresPermissions("system:role:list")
    public AjaxResult list(SysRoleQueryDTO query) {
        return AjaxResult.success("成功", sysRoleService.listRoleInfo(query));
    }

    @Log(title = "角色管理", businessType = BusinessType.QUERY, isSaveResponseData = false)
    @GetMapping("/options")
    @RequiresPermissions("system:role:list")
    public AjaxResult roleOptions() {
        return AjaxResult.success("成功", sysRoleService.listAllRoleOptions());
    }

    @Log(title = "角色管理", businessType = BusinessType.INSERT)
    @PostMapping
    @RequiresPermissions("system:role:add")
    public AjaxResult add(@Valid @RequestBody SysRoleCreateDTO dto) {
        sysRoleService.createRole(dto);
        return AjaxResult.success("新增成功", null);
    }

    @Log(title = "角色管理", businessType = BusinessType.UPDATE)
    @PutMapping
    @RequiresPermissions("system:role:edit")
    public AjaxResult update(@Valid @RequestBody SysRoleUpdateDTO dto) {
        sysRoleService.updateRole(dto);
        return AjaxResult.success("更新成功", null);
    }

    @Log(title = "角色管理", businessType = BusinessType.GRANT)
    @PutMapping("/authPerm")
    @RequiresPermissions("system:role:edit")
    public AjaxResult authPerm(@Valid @RequestBody SysRolePermAssignDTO dto) {
        sysRoleService.assignRolePermissions(dto);
        return AjaxResult.success("分配权限成功", null);
    }

    @Log(title = "角色管理", businessType = BusinessType.DELETE)
    @DeleteMapping("/{roleId}")
    @RequiresPermissions("system:role:delete")
    public AjaxResult delete(@PathVariable Long roleId) {
        sysRoleService.deleteRole(roleId);
        return AjaxResult.success("删除成功", null);
    }
}
