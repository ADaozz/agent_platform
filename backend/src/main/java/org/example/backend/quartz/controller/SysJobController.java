package org.example.backend.quartz.controller;

import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.example.backend.common.annotation.Log;
import org.example.backend.common.enums.BusinessType;
import org.example.backend.common.result.AjaxResult;
import org.example.backend.quartz.dto.SysJobQueryDTO;
import org.example.backend.quartz.dto.SysJobUpdateDTO;
import org.example.backend.quartz.service.SysJobService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;
import javax.validation.constraints.NotNull;
import javax.validation.constraints.Pattern;

/**
 * 定时任务：任务由代码扫描注册，仅允许查询与修改，不提供新增/删除接口。
 */
@RestController
@Validated
@RequestMapping("/monitor/job")
public class SysJobController {

    @Autowired
    private SysJobService sysJobService;

    @Log(title = "定时任务", businessType = BusinessType.QUERY)
    @GetMapping
    @RequiresPermissions("monitor:job:list")
    public AjaxResult list(SysJobQueryDTO query) {
        return AjaxResult.success("成功", sysJobService.listSysJob(query));
    }

    @Log(title = "定时任务", businessType = BusinessType.UPDATE)
    @PutMapping
    @RequiresPermissions("monitor:job:edit")
    public AjaxResult update(@Valid @RequestBody SysJobUpdateDTO dto) {
        sysJobService.updateSysJob(dto);
        return AjaxResult.success("更新成功", null);
    }

    @Log(title = "定时任务", businessType = BusinessType.UPDATE)
    @PutMapping("/changeStatus")
    @RequiresPermissions("monitor:job:edit")
    public AjaxResult changeStatus(
            @RequestParam @NotNull(message = "任务ID不能为空") Long jobId,
            @RequestParam @Pattern(regexp = "[01]", message = "启用状态只能是0或1") String enabled) {
        sysJobService.changeJobEnabled(jobId, enabled);
        return AjaxResult.success("状态更新成功", null);
    }

    @Log(title = "定时任务", businessType = BusinessType.UPDATE)
    @PutMapping("/run")
    @RequiresPermissions("monitor:job:edit")
    public AjaxResult run(@RequestParam @NotNull(message = "任务ID不能为空") Long jobId) {
        sysJobService.runJobOnce(jobId);
        return AjaxResult.success("执行成功", null);
    }
}
