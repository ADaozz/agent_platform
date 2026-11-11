package org.example.backend.statistics.controller;

import org.example.backend.common.annotation.Log;
import org.example.backend.common.enums.BusinessType;
import org.example.backend.common.result.AjaxResult;
import org.example.backend.statistics.constant.DashboardScope;
import org.example.backend.statistics.service.DashboardService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 仪表盘：scope=mine 看当前用户 owner 数据；scope=all 需 dashboard:view:all。
 */
@RestController
@RequestMapping("/dashboard")
public class DashboardController {

    @Autowired
    private DashboardService dashboardService;

    @Log(title = "仪表盘", businessType = BusinessType.QUERY, isSaveResponseData = false)
    @GetMapping("/overview")
    public AjaxResult overview(@RequestParam(defaultValue = DashboardScope.MINE) String scope) {
        return AjaxResult.success("成功", dashboardService.getOverview(scope));
    }

    @Log(title = "仪表盘", businessType = BusinessType.QUERY, isSaveResponseData = false)
    @GetMapping("/summary")
    public AjaxResult summary(@RequestParam(defaultValue = DashboardScope.MINE) String scope) {
        return AjaxResult.success("成功", dashboardService.getOverview(scope));
    }

    @Log(title = "仪表盘", businessType = BusinessType.QUERY, isSaveResponseData = false)
    @GetMapping("/kpi")
    public AjaxResult kpi(@RequestParam(defaultValue = DashboardScope.MINE) String scope) {
        return AjaxResult.success("成功", dashboardService.getKpi(scope));
    }

    @Log(title = "仪表盘", businessType = BusinessType.QUERY, isSaveResponseData = false)
    @GetMapping("/vm/by-lifecycle")
    public AjaxResult vmByLifecycle(@RequestParam(defaultValue = DashboardScope.MINE) String scope) {
        return AjaxResult.success("成功", dashboardService.getVmByLifecycle(scope));
    }

    @Log(title = "仪表盘", businessType = BusinessType.QUERY, isSaveResponseData = false)
    @GetMapping("/vm/by-env")
    public AjaxResult vmByEnv(@RequestParam(defaultValue = DashboardScope.MINE) String scope) {
        return AjaxResult.success("成功", dashboardService.getVmByEnv(scope));
    }

    @Log(title = "仪表盘", businessType = BusinessType.QUERY, isSaveResponseData = false)
    @GetMapping("/vm/by-network-zone")
    public AjaxResult vmByNetworkZone(@RequestParam(defaultValue = DashboardScope.MINE) String scope) {
        return AjaxResult.success("成功", dashboardService.getVmByNetworkZone(scope));
    }

    @Log(title = "仪表盘", businessType = BusinessType.QUERY, isSaveResponseData = false)
    @GetMapping("/app/by-status")
    public AjaxResult appByStatus(@RequestParam(defaultValue = DashboardScope.MINE) String scope) {
        return AjaxResult.success("成功", dashboardService.getAppByStatus(scope));
    }

    @Log(title = "仪表盘", businessType = BusinessType.QUERY, isSaveResponseData = false)
    @GetMapping("/trend/vm")
    public AjaxResult vmCreateTrend(@RequestParam(defaultValue = DashboardScope.MINE) String scope) {
        return AjaxResult.success("成功", dashboardService.getVmCreateTrend(scope));
    }

    @Log(title = "仪表盘", businessType = BusinessType.QUERY, isSaveResponseData = false)
    @GetMapping("/rank/owner")
    public AjaxResult ownerRank() {
        return AjaxResult.success("成功", dashboardService.getOwnerRank());
    }

    @Log(title = "仪表盘", businessType = BusinessType.QUERY, isSaveResponseData = false)
    @GetMapping("/vm/by-physical-host")
    public AjaxResult physicalHostDistribution() {
        return AjaxResult.success("成功", dashboardService.getPhysicalHostDistribution());
    }
}
