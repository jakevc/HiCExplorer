import numpy as np

import logging
log = logging.getLogger(__name__)


class Viewpoint():

    def __init__(self, pHiCMatrix=None):
        self.hicMatrix = pHiCMatrix

    def setHiCMatrixObj(self, pHiCMatrix):
        self.hicMatrix = pHiCMatrix

    def readReferencePointFile(self, pBedFile):
        viewpoints = []

        with open(pBedFile, 'r') as file:
            for line in file.readlines():
                line_ = line.strip().split('\t')
                if len(line) == 0:
                    continue
                if len(line_) == 2:
                    chrom, start, end = line_[0], line_[1], line_[1]
                else:
                    chrom, start, end = line_
                viewpoints.append((chrom, start, end))
        return viewpoints

    def readInteractionFile(self, pBedFile):
        # use header info to store reference point, and based matrix
        interaction_data = {}
        z_score = {}
        interaction_file_data = {}
        with open(pBedFile) as fh:
            header = fh.readline()
            for line in fh.readlines():
                # Addition header information for end users
                if line.strip().startswith('#'):
                    continue

                line_ = line.strip().split('\t')
                # relative postion and relative interactions
                interaction_data[int(line_[-3])] = float(line_[-2])
                z_score[int(line_[-3])] = float(line_[-1])
                interaction_file_data[int(line_[-3])] = line_
        return header, interaction_data, z_score, interaction_file_data

    def readBackgroundDataFile(self, pBedFile):

        distance = {}
        with open(pBedFile) as fh:
            for line in fh.readlines():
                line_ = line.split('\t')
                distance[int(line_[0])] = [float(line_[1]), float(line_[2])]

        return distance

    def writeInteractionFile(self, pBedFile, pData, pHeader, pZscoreData):
        with open(pBedFile + '.bed', 'w') as fh:
            fh.write('#{}\n'.format(pHeader))
            for j, interaction in enumerate(pData):
                fh.write("{}\t{}\t{}\t{}\t{}\t{}\t{}\t{:.12f}\t{:.12f}\n".
                         format(interaction[0], interaction[1], interaction[2],
                                interaction[3], interaction[4], interaction[5],
                                interaction[6], interaction[7], pZscoreData[j]))
        return

    def computeViewpoint(self, pReferencePoint, pChromViewpoint, pRegion_start, pRegion_end):
        view_point_start, view_point_end = self.getReferencePointAsMatrixIndices(pReferencePoint)

        view_point_range = self.getViewpointRangeAsMatrixIndices(pChromViewpoint, pRegion_start, pRegion_end)

        elements_of_viewpoint = (view_point_range[1] - view_point_range[0])

        data_list = np.zeros(elements_of_viewpoint)
        view_point_start_ = view_point_start
        # interactions_list = None

        while view_point_start_ <= view_point_end:
            chrom, start, end, _ = self.hicMatrix.getBinPos(view_point_start_)
            # index_viewpoint = 0
            for j, idx in zip(range(elements_of_viewpoint), range(view_point_range[0], view_point_range[1], 1)):
                # if j < view_point_start:
                #     index_viewpoint = j
                # elif j > view_point_end:
                #     index_viewpoint = j
                data_list[j] += self.hicMatrix.matrix[view_point_start_, idx]

            view_point_start_ += 1

        elements_of_viewpoint = elements_of_viewpoint - (view_point_end - view_point_start)
        data_list_new = np.zeros(elements_of_viewpoint)

        index_before_viewpoint = view_point_start - view_point_range[0]

        # elements before the viewpoint
        data_list_new[0:index_before_viewpoint] = data_list[0:index_before_viewpoint]

        # summation because the viewpoint can be not only one bin but can contain multiple
        data_list_new[index_before_viewpoint] = np.sum(data_list[index_before_viewpoint: index_before_viewpoint + view_point_end - view_point_start + 1])

        # elements after the viewpoint
        data_list_new[index_before_viewpoint + 1:] = data_list[index_before_viewpoint + view_point_end - view_point_start + 1:]
        return data_list_new

    def createInteractionFileData(self, pReferencePoint, pChromViewpoint, pRegion_start, pRegion_end, pInteractionData):

        view_point_start, view_point_end = self.getReferencePointAsMatrixIndices(pReferencePoint)
        view_point_range = self.getViewpointRangeAsMatrixIndices(pChromViewpoint, pRegion_start, pRegion_end)
        elements_of_viewpoint = view_point_range[1] - view_point_range[0] - (view_point_end - view_point_start) + 1

        interactions_list = []
        chrom, start, _, _ = self.hicMatrix.getBinPos(view_point_start)
        _, _, end, _ = self.hicMatrix.getBinPos(view_point_end)
        interaction_positions = list(range(view_point_range[0], view_point_start, 1))
        interaction_positions.extend([view_point_start])
        interaction_positions.extend(list(range(view_point_end + 1, view_point_range[1], 1)))
        relative_position = -1
        for j, idx in zip(range(elements_of_viewpoint), interaction_positions):

            chrom_second, start_second, end_second, _ = self.hicMatrix.getBinPos(idx)
            if relative_position < 0:
                relative_position = int(start_second) - int(start)
            else:
                relative_position = int(end_second) - int(end)

            interactions_list.append((chrom, start, end, chrom_second, start_second, end_second, relative_position, float(pInteractionData[j])))

        return interactions_list

    def getViewpointRangeAsMatrixIndices(self, pChromViewpoint, pRegion_start, pRegion_end):

        return self.hicMatrix.getRegionBinRange(pChromViewpoint, pRegion_start, pRegion_end)

    def getReferencePointAsMatrixIndices(self, pReferencePoint):
        if len(pReferencePoint) == 2:
            view_point_start, view_point_end = self.hicMatrix.getRegionBinRange(pReferencePoint[0], int(pReferencePoint[1]), int(pReferencePoint[1]))
        elif len(pReferencePoint) == 3:
            view_point_start, view_point_end = self.hicMatrix.getRegionBinRange(pReferencePoint[0], int(pReferencePoint[1]), int(pReferencePoint[2]))
        else:
            log.error("No valid reference point given. {}".format(pReferencePoint))
            exit(1)
        return view_point_start, view_point_end

    def smoothInteractionValues(self, pData, pWindowSize):

        window_size = np.int(np.floor(pWindowSize / 2))
        window_size_upstream = window_size
        if pWindowSize % 2 == 0:
            window_size_upstream -= 1

        average_contacts = np.zeros(len(pData))

        # add upstream and downstream, handle regular case
        for i in range(window_size_upstream, len(pData) - window_size):
            start = i - window_size_upstream
            end = i + window_size + 1
            average_contacts[i] = np.mean(pData[start:end])

        # handle border conditions
        for i in range(window_size):
            start = i - window_size_upstream
            if start < 0:
                start = 0
            end = i + window_size + 1

            average_contacts[i] = np.mean(pData[start:end])
            average_contacts[-(i + 1)] = np.mean(pData[-end:])
        return average_contacts

    def computeRelativeValues(self, pData):
        sumValue = np.sum(pData)
        pData /= sumValue
        return pData

    def calculateViewpointRange(self, pViewpoint, pRange):
        max_length = self.hicMatrix.getBinPos(self.hicMatrix.getChrBinRange(pViewpoint[0])[1] - 1)[2]

        region_start = int(pViewpoint[1]) - pRange[0]
        if region_start < 0:
            region_start = 0

        region_end = int(pViewpoint[2]) + pRange[1]
        if region_end > max_length:
            region_end = max_length - 1

        return region_start, region_end
