package org.example.backend.asset.host.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.experimental.Accessors;
import org.springframework.format.annotation.DateTimeFormat;

import java.util.Date;

@Data
@TableName("vm_host")
@Accessors(chain = true)
@EqualsAndHashCode(callSuper = false)
public class VmHostEntity {

    @TableId(type = IdType.ASSIGN_UUID)
    // 虚机 ID（UUID）
    private String hostId;

    // 虚机名称
    private String hostName;

    // 操作系统类型
    private String osType;

    // 操作系统版本
    private String osVersion;

    // 虚机 IP 地址
    private String vmIp;

    // CPU 核数
    private Integer cpuCores;

    // 内存大小（GB）
    private Integer memoryGb;

    // 磁盘大小（GB）
    private Integer diskGb;

    // 物理宿主机 IP 地址
    private String physicalHostIp;

    // 生命周期状态：creating-创建中，running-运行中，stopped-已停止，
    // pending_delete-待删除，destroyed-已销毁
    private String lifecycleStatus;

    // 所属用户 ID（虚机负责人）
    private Long ownerUserId;

    // 网络区域：idc-IDC 机房，cfdc-CFDC
    private String networkZone;

    // 部署环境：prod-生产，dev-开发，test-测试
    private String env;

    // 备注
    private String remark;

    @JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    // 创建时间
    private Date createTime;

    @JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    // 更新时间
    private Date updateTime;
}
