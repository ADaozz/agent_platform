package org.example.backend.quartz.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import lombok.extern.slf4j.Slf4j;
import org.example.backend.common.exception.BusinessException;
import org.example.backend.common.exception.Module;
import org.example.backend.common.vo.PageResultVO;
import org.example.backend.quartz.constant.SysJobConstants;
import org.example.backend.quartz.dto.SysJobQueryDTO;
import org.example.backend.quartz.dto.SysJobUpdateDTO;
import org.example.backend.quartz.entity.SysJobEntity;
import org.example.backend.quartz.mapper.SysJobMapper;
import org.example.backend.quartz.service.JobTaskExecutor;
import org.example.backend.quartz.service.QuartzSchedulerService;
import org.example.backend.quartz.service.SysJobService;
import org.example.backend.quartz.vo.SysJobVO;
import org.springframework.context.annotation.Lazy;
import org.springframework.scheduling.support.CronExpression;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import javax.annotation.Resource;
import java.util.Collections;
import java.util.Date;
import java.util.List;
import java.util.stream.Collectors;

@Slf4j
@Service
public class SysJobServiceImpl extends ServiceImpl<SysJobMapper, SysJobEntity> implements SysJobService {

    @Resource
    private SysJobMapper sysJobMapper;

    @Resource
    private JobTaskExecutor jobTaskExecutor;

    @Lazy
    @Resource
    private QuartzSchedulerService quartzSchedulerService;

    @Override
    // 分页查询定时任务列表
    public PageResultVO<SysJobVO> listSysJob(SysJobQueryDTO dto) {
        if (dto.getJobId() != null) {
            SysJobVO vo = toSysJobVO(getJobOrThrow(dto.getJobId()));
            return new PageResultVO<>(1, Collections.singletonList(vo));
        }

        LambdaQueryWrapper<SysJobEntity> wrapper = buildQueryWrapper(dto);
        int pageNum = dto.getPageNum() != null ? dto.getPageNum() : 1;
        int pageSize = dto.getPageSize() != null ? dto.getPageSize() : 10;
        Page<SysJobEntity> page = page(new Page<>(pageNum, pageSize), wrapper);

        List<SysJobVO> rows = page.getRecords().stream()
                .map(this::toSysJobVO)
                .collect(Collectors.toList());
        return new PageResultVO<>(page.getTotal(), rows);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    // 更新定时任务配置
    public void updateSysJob(SysJobUpdateDTO dto) {
        SysJobEntity job = getJobOrThrow(dto.getJobId());

        validateCronExpression(dto.getCronExpression());

        String targetEnabled = StringUtils.hasText(dto.getEnabled()) ? dto.getEnabled() : job.getEnabled();
        if (SysJobConstants.ENABLED_YES.equals(targetEnabled)) {
            assertCanEnable(dto.getCronExpression());
        }

        job.setJobName(dto.getJobName());
        job.setCronExpression(dto.getCronExpression());
        job.setDescription(dto.getDescription());
        if (StringUtils.hasText(dto.getEnabled())) {
            job.setEnabled(dto.getEnabled());
        }
        job.setUpdateTime(new Date());
        updateById(job);

        quartzSchedulerService.syncJob(job);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    // 切换定时任务启用状态
    public void changeJobEnabled(Long jobId, String enabled) {
        if (!SysJobConstants.ENABLED_YES.equals(enabled) && !SysJobConstants.ENABLED_NO.equals(enabled)) {
            throw new BusinessException(Module.ModuleType.QUARTZ, "启用状态只能是0或1", null);
        }

        SysJobEntity job = getJobOrThrow(jobId);
        if (SysJobConstants.ENABLED_YES.equals(enabled)) {
            assertCanEnable(job.getCronExpression());
        }

        job.setEnabled(enabled);
        job.setUpdateTime(new Date());
        updateById(job);

        quartzSchedulerService.syncJob(job);
    }

    @Override
    // 立即执行一次定时任务
    public void runJobOnce(Long jobId) {
        SysJobEntity job = getJobOrThrow(jobId);
        if (!SysJobConstants.ENABLED_YES.equals(job.getEnabled())) {
            throw new BusinessException(Module.ModuleType.QUARTZ, "任务未启用，无法执行", null);
        }
        jobTaskExecutor.execute(job, true);
    }

    @Override
    // 获取定时任务或抛出不存在异常
    public SysJobEntity getJobOrThrow(Long jobId) {
        SysJobEntity job = getById(jobId);
        if (job == null) {
            throw new BusinessException(Module.ModuleType.QUARTZ, "定时任务不存在", null);
        }
        return job;
    }

    // 构建定时任务查询条件
    private LambdaQueryWrapper<SysJobEntity> buildQueryWrapper(SysJobQueryDTO dto) {
        LambdaQueryWrapper<SysJobEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.like(StringUtils.hasText(dto.getJobName()), SysJobEntity::getJobName, dto.getJobName())
                .eq(StringUtils.hasText(dto.getJobGroup()), SysJobEntity::getJobGroup, dto.getJobGroup())
                .eq(StringUtils.hasText(dto.getEnabled()), SysJobEntity::getEnabled, dto.getEnabled())
                .orderByAsc(SysJobEntity::getJobId);
        return wrapper;
    }

    // 将任务实体转换为VO
    private SysJobVO toSysJobVO(SysJobEntity entity) {
        SysJobVO vo = new SysJobVO();
        vo.setJobId(entity.getJobId());
        vo.setJobName(entity.getJobName());
        vo.setBeanName(entity.getBeanName());
        vo.setJobGroup(entity.getJobGroup());
        vo.setCronExpression(entity.getCronExpression());
        vo.setDescription(entity.getDescription());
        vo.setStatus(entity.getStatus());
        vo.setEnabled(entity.getEnabled());
        vo.setCreateTime(entity.getCreateTime());
        vo.setUpdateTime(entity.getUpdateTime());
        return vo;
    }

    // 校验Cron表达式合法性
    private void validateCronExpression(String cronExpression) {
        if (!StringUtils.hasText(cronExpression)) {
            return;
        }
        try {
            CronExpression.parse(cronExpression);
        } catch (IllegalArgumentException e) {
            throw new BusinessException(Module.ModuleType.QUARTZ, "Cron 表达式不合法", null);
        }
    }

    // 校验任务是否满足启用条件
    private void assertCanEnable(String cronExpression) {
        if (!StringUtils.hasText(cronExpression)) {
            throw new BusinessException(Module.ModuleType.QUARTZ, "请先配置 Cron 表达式后再启用", null);
        }
        validateCronExpression(cronExpression);
    }
}
