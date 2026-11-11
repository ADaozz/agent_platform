package org.example.backend.statistics.vo.chart;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;

/**
 * 饼图 / 环形图。
 * 前端：series[0].data = data
 */
@Data
public class PieChartVO {

    private List<PieItemVO> data = new ArrayList<>();
}
